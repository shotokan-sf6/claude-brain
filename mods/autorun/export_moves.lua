-- export_moves.lua (REFramework, Street Fighter 6)
-- Exports, for the two characters currently loaded in a match (training mode is easiest):
--   reframework/data/sf6_moves/<id>_<Name>.json : action id -> move/animation name
-- and once, the game's state enums:
--   reframework/data/sf6_moves/enums.json       : act_st, action and other battle enums -> names
-- capture_replay.lua reads these files and adds move names to each saved replay.
--
-- Use: load training mode with the characters you want, open the REFramework menu (Insert),
-- and press "Export moves for both characters" under Script Generated UI > "Move Export".
-- Written for Sean's replay reviews; uses the same game structures as rkaganda/sf6_replays_data
-- and alphazolam's MMDK, which documented where the move tables live.

-- Character names come from one place: reframework/data/sf6_moves/char_names.json ({"9": "Cammy", ...}), shared with
-- capture_replay.lua and the analyzer. A character missing from it is saved as "char_<id>" until you name it in the
-- window: it shows both characters' IDs live, and "Save names" adds them to char_names.json.
local NAMES_FILE = "sf6_moves/char_names.json"
local saved = json.load_file(NAMES_FILE) or {}
local CHARACTERS = {}
for k, v in pairs(saved) do CHARACTERS[tonumber(k)] = v end
local typed = { [0] = "", [1] = "" }

local ENUMS = { "nBattle.ACT_ST.ID", "nBattle.ACT_ID", "nBattle.POSE_ST", "nBattle.POSE_ST.ID", "nBattle.DMG_TYPE", "nBattle.HIT_TYPE" }

local VERSION = "v4.1"
local step = ""
local status = "Load a match (training mode works) and press Export."

local function safe(fn, default)
    local ok, v = pcall(fn)
    if ok then return v end
    return default
end


-- read a managed array / List / dictionary-entries array into a Lua list (no pairs() on game objects)
local function to_list(arr)
    local out = {}
    if arr == nil then return out end
    local elems = safe(function() return arr:get_elements() end)
    if type(elems) == "table" then
        for _, v in ipairs(elems) do out[#out + 1] = v end
        return out
    end
    local items = safe(function() return arr._items end)
    local n = safe(function() return arr._size end)
    if items and n then
        for i = 0, n - 1 do out[#out + 1] = safe(function() return items[i] end) end
        return out
    end
    n = safe(function() return arr:get_size() end) or safe(function() return arr:call("get_Count()") end) or safe(function() return arr.Length end)
    if n then
        for i = 0, n - 1 do out[#out + 1] = safe(function() return arr[i] end) end
    end
    return out
end

local function enum_table(typename)
    local t = sdk.find_type_definition(typename)
    if not t then return nil end
    local out, any = {}, false
    for _, f in ipairs(t:get_fields()) do
        if f:is_static() then
            local v = safe(function() return f:get_data(nil) end)
            if type(v) == "number" then out[tostring(v)] = f:get_name(); any = true end
        end
    end
    return any and out or nil
end

local function export_enums()
    local all = {}
    for _, name in ipairs(ENUMS) do
        local e = enum_table(name)
        if e then all[name] = e end
    end
    json.dump_file("sf6_moves/enums.json", all)
    return all
end

local function dict_values(dict)
    local out = {}
    for _, entry in ipairs(to_list(safe(function() return dict._entries end))) do
        local v = safe(function() return entry.value end)
        if v ~= nil then out[#out + 1] = v end
    end
    return out
end

local function motion_name(motion, mot_info, mtype, mid)
    if not motion or mtype == nil or mid == nil then return nil end
    return safe(function()
        motion:call("getMotionInfo(System.UInt32, System.UInt32, via.motion.MotionInfo)", mtype, mid, mot_info)
        return mot_info:get_MotionName()
    end)
end

local function export_player(i, act_enum)
    local gBattle = sdk.find_type_definition("gBattle")
    local gPlayer = gBattle:get_field("Player"):get_data()
    local gResource = gBattle:get_field("Resource"):get_data()
    step = "reading character"
    local char_id = gPlayer.mPlayerType[i].mValue
    local char_name = CHARACTERS[char_id] or ("char_" .. tostring(char_id))
    local person = gResource.Data[i]
    if not person then return char_name .. ": no data" end
    local motion = safe(function() return gBattle:get_field("PBManager"):get_data().Players[i].mpMot end)
    local mot_info = sdk.create_instance("via.motion.MotionInfo"):add_ref()

    local moves, count = {}, 0
    step = "reading move tables"
    local styles = safe(function() return person.FAB.StyleDict:call("get_Count()") end, 0)
    for s = 0, styles - 1 do
        local style = safe(function() return person.FAB.StyleDict[s] end)
            or safe(function() return person.FAB.StyleDict:call("get_Item", s) end)
        if style then
            for _, fab in ipairs(dict_values(style.ActionList)) do
                local id = safe(function() return fab.ActionID end)
                if id ~= nil then
                    local key = string.format("%04d", id)
                    if not moves[key] then
                        local mot = motion_name(motion, mot_info, safe(function() return fab.MotionType end), safe(function() return fab.MotionID end))
                        if not mot then
                            -- fall back to the first motion key inside the action
                            for _, list in ipairs(to_list(safe(function() return fab.Keys end))) do
                                local first = to_list(list)[1]
                                if first and safe(function() return first:get_type_definition():get_name() end) == "MotionKey" then
                                    mot = motion_name(motion, mot_info, first.MotionType, first.MotionID)
                                    if mot then break end
                                end
                            end
                        end
                        local clean = mot and mot:gsub("^esf%d+_", "") or nil
                        moves[key] = { id = id, name = clean or (act_enum and act_enum[tostring(id)]) or ("_" .. key),
                                       motion = mot, enum = act_enum and act_enum[tostring(id)] or nil, style = s }
                        count = count + 1
                    end
                end
            end
        end
    end
    step = "saving file"
    local file = string.format("sf6_moves/%02d_%s.json", char_id, char_name:gsub("[^%w%-]", "_"))
    json.dump_file(file, { char_id = char_id, char_name = char_name, moves = moves })
    return char_name .. ": " .. count .. " moves"
end

local function live_ids()
    return safe(function()
        local gPlayer = sdk.find_type_definition("gBattle"):get_field("Player"):get_data()
        return { [0] = gPlayer.mPlayerType[0].mValue, [1] = gPlayer.mPlayerType[1].mValue }
    end)
end

-- UI lives under "Script Generated UI" in the REFramework menu (Insert), like Batch replays.
re.on_draw_ui(function()
    if not imgui.tree_node("Move Export " .. VERSION) then return end
    local ids = live_ids()
    if ids then
        for i = 0, 1 do
            local id = ids[i]
            imgui.text(string.format("P%d: character ID %s = %s", i + 1, tostring(id), CHARACTERS[id] or "(not named yet)"))
            if CHARACTERS[id] == nil then
                local changed, v = imgui.input_text("Name for ID " .. tostring(id) .. "##p" .. i, typed[i])
                if changed then typed[i] = v end
            end
        end
        if (typed[0] ~= "" or typed[1] ~= "") and imgui.button("Save names") then
            for i = 0, 1 do
                if typed[i] ~= "" and ids[i] ~= nil then
                    CHARACTERS[ids[i]] = typed[i]; saved[tostring(ids[i])] = typed[i]; typed[i] = ""
                end
            end
            json.dump_file(NAMES_FILE, saved)
            status = "Names saved. Press Export to re-save the move files with the new names."
        end
    else
        imgui.text("Load a match to see the character IDs.")
    end
    if imgui.button("Export moves for both characters") then
        local enums = safe(export_enums, {})
        local act_enum = enums and enums["nBattle.ACT_ID"] or nil
        local ok1, r1 = pcall(export_player, 0, act_enum)
        local ok2, r2 = pcall(export_player, 1, act_enum)
        if not ok1 then r1 = "P1 failed while " .. step .. ": " .. tostring(r1) end
        if not ok2 then r2 = "P2 failed while " .. step .. ": " .. tostring(r2) end
        status = "Saved to reframework/data/sf6_moves: " .. tostring(r1) .. "; " .. tostring(r2)
    end
    imgui.text(status)
    imgui.tree_pop()
end)
