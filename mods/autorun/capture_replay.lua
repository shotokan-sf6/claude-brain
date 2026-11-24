-- capture_replay.lua (REFramework, Street Fighter 6)
-- Records every frame of a replay and auto-saves it to reframework/data/<replayid>.json
-- when the match ends. Based on rkaganda/SF6_replay_capture and rkaganda/sf6_replays_data,
-- with fixes plus inputs, burnout, battle stats and hit data.
--
-- Per frame, per player: action id/frame, HP, Drive, super, burnout, position/speed,
--   hitstun/blockstun/hitstop, invulnerability, juggle, combo count/damage, raw input bits.
-- Per hit: every numeric field of the victim's damage_info (used to find the counter hit /
--   punish counter flag), attacker combo count/damage.
-- Battle stats (perfect parries, throw techs, Drive Reversals, Drive Impacts, ...): saved only
--   when a value changes, so the file shows when each one happened.

local CHARACTERS = {
    [1] = "Ryu", [2] = "Luke", [3] = "Kimberly", [4] = "Chun-Li", [5] = "Manon", [6] = "Zangief",
    [7] = "JP", [8] = "Dhalsim", [9] = "Cammy", [10] = "Ken", [11] = "Dee Jay", [12] = "Lily",
    [13] = "AKI", [14] = "Rashid", [15] = "Blanka", [16] = "Juri", [17] = "Marisa", [18] = "Guile",
    [19] = "Ed", [20] = "E Honda", [21] = "Jamie", [22] = "Akuma", [26] = "M Bison", [27] = "Terry",
    [28] = "Mai",
}
-- names typed into Move Export v4.1 (sf6_moves/char_names.json) cover characters missing from the list above
local function load_char_names()
    local ok, saved = pcall(json.load_file, "sf6_moves/char_names.json")
    if ok and type(saved) == "table" then
        for k, v in pairs(saved) do CHARACTERS[tonumber(k)] = v end
    end
end
load_char_names()

local autosave = true
local capture_projectiles = true
local recording = true
local manual_filename = "replay.json"
local filename_changed

local replay, frames_captured, hits_captured
local last_key, last_error, last_saved
local last_stats, last_hitstun, last_combo, last_charge, last_proj
local game_saved = false
local idle_frames = 0       -- frames spent out of a fight (fight_st 0)

local function clear()
    replay = { info = {}, frames = {}, hits = {}, stats = {}, charge = {}, projectiles = {} }
    frames_captured, hits_captured = 0, 0
    last_key, last_error = nil, nil
    last_stats = { {}, {} }
    last_hitstun = { 0, 0 }
    last_combo = { 0, 0 }
    last_charge = { "", "" }
    last_proj = {}
end
clear()

local function bitand(a, b)
    local result, bitval = 0, 1
    while a > 0 and b > 0 do
        if a % 2 == 1 and b % 2 == 1 then result = result + bitval end
        bitval = bitval * 2
        a = math.floor(a / 2)
        b = math.floor(b / 2)
    end
    return result
end

local function read_sfix(sfix_obj)
    if sfix_obj == nil then return nil end
    return tonumber(sfix_obj:call("ToString()"))
end

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

-- every numeric / boolean instance field of a managed object or struct
local function dump_fields(obj)
    local out = {}
    if obj == nil then return out end
    local td = safe(function() return obj:get_type_definition() end)
    if not td then return out end
    for _, f in ipairs(td:get_fields()) do
        if not f:is_static() then
            local name = f:get_name()
            local v = safe(function() return obj[name] end)
            local t = type(v)
            if t == "number" or t == "boolean" then out[name] = v end
        end
    end
    return out
end

local function enum_table(typename)
    local t = sdk.find_type_definition(typename)
    if not t then return {} end
    local out = {}
    for _, f in ipairs(t:get_fields()) do
        if f:is_static() then
            local v = safe(function() return f:get_data(nil) end)
            if type(v) == "number" then out[v] = f:get_name() end
        end
    end
    return out
end
local ACT_ST_NAMES = safe(function() return enum_table("nBattle.ACT_ST.ID") end, {})

-- serialise a table of numbers/booleans to a short string, for change detection
local function sig(t)
    local keys = {}
    for k in pairs(t) do keys[#keys + 1] = k end
    table.sort(keys)
    local parts = {}
    for _, k in ipairs(keys) do parts[#parts + 1] = k .. "=" .. tostring(t[k]) end
    return table.concat(parts, ",")
end

-- add move names from export_moves.lua's files, if they exist
local function attach_move_names()
    replay.move_names = {}
    for _, side in ipairs({ "p1", "p2" }) do
        local id = replay.info[side .. "_char_id"]
        local name = replay.info[side .. "_char"]
        if id and name then
            local file = string.format("sf6_moves/%02d_%s.json", id, name:gsub("[^%w%-]", "_"))
            local data = safe(function() return json.load_file(file) end)
            if data and data.moves then
                local m = {}
                for k, v in pairs(data.moves) do m[k] = v.name end
                replay.move_names[side] = m
            end
        end
    end
end

-- replay ID, player names and round results of the replay being watched
local function read_replay_info()
    load_char_names()  -- pick up names saved since the script loaded
    local mgr = sdk.get_managed_singleton("app.BattleReplayDataManager")
    if not mgr then return end
    local item = safe(function() return mgr._ReplayList._items[0] end)
    if not item then return end
    replay.info.replay_id = safe(function() return item.ReplayID end)
    replay.info.p1_name = safe(function() return item.ReplayInfo.player1_info.player.fighter_id end)
    replay.info.p2_name = safe(function() return item.ReplayInfo.player2_info.player.fighter_id end)
    replay.info.battle_type = safe(function() return item.ReplayInfo.replay_battle_type end)
    -- CFN ID (Buckler "short_id", e.g. .shog = 1307078698) and rank info, when the replay data carries them
    for n, key in ipairs({ "player1_info", "player2_info" }) do
        local pi = safe(function() return item.ReplayInfo[key] end)
        local pl = pi and safe(function() return pi.player end)
        local side = "p" .. n
        local sid = pl and safe(function() return pl.short_id end)
        replay.info[side .. "_cfn_id"] = sid ~= nil and tostring(sid) or nil
        replay.info[side .. "_platform"] = pl and safe(function() return pl.platform_name end)
        replay.info[side .. "_mr"] = pi and safe(function() return pi.master_rating end)
        replay.info[side .. "_lp"] = pi and safe(function() return pi.league_point end)
        -- one-off discovery: list the field names on the player objects so missing IDs can be found
        if replay.info.player_fields == nil then
            replay.info.player_fields = {}
            for _, obj in ipairs({ pi, pl }) do
                local td = obj and safe(function() return obj:get_type_definition() end)
                if td then
                    for _, f in ipairs(td:get_fields()) do
                        replay.info.player_fields[#replay.info.player_fields + 1] = td:get_name() .. "." .. f:get_name()
                    end
                end
            end
        end
    end
    local rounds = safe(function() return item.ReplayData.ReplayInfo.RoundInfo end)
    if rounds then
        replay.info.round_results = {}
        for i, r in ipairs(to_list(rounds)) do
            replay.info.round_results[#replay.info.round_results + 1] = {
                round = i, win_player = safe(function() return r.WinPlayerType end),
                finish_type = safe(function() return r.FinishType end) }
        end
    end
end

local function save(filename)
    safe(attach_move_names)
    if json.dump_file(filename, replay) then
        last_saved = filename .. " (" .. frames_captured .. " frames, " .. hits_captured .. " hits)"
        return true
    end
    last_error = "Save failed: " .. filename
    return false
end

local function read_player(i, cPlayer, cTeam, engine, inputInfo)
    local pl, team = cPlayer[i], cTeam[i]
    local p = {}
    p.action_id = safe(function() return engine:get_ActionID() end)
    p.action_frame = safe(function() return math.floor(read_sfix(engine:get_ActionFrame())) end)
    p.end_frame = safe(function() return math.floor(read_sfix(engine:get_ActionFrameNum())) end)
    p.margin_frame = safe(function() return math.floor(read_sfix(engine:get_MarginFrame())) end)
    p.hp = pl.vital_new
    p.hp_recoverable_cap = safe(function() return pl.heal_new end)
    p.hp_cooldown = pl.healing_wait
    p.drive = pl.focus_new
    p.drive_cooldown = pl.focus_wait
    p.burnout = safe(function() return pl.incapacitated end)
    p.super = team.mSuperGauge
    p.combo_count = safe(function() return team.mComboCount end)
    p.combo_damage = safe(function() return team.mComboDamage end)
    p.dir = (bitand(pl.BitValue, 128) == 128) and 1 or 0
    p.hitstop = pl.hit_stop
    p.hitstun = pl.damage_time
    p.blockstun = pl.guard_time
    p.stance = pl.pose_st
    p.act_st = pl.act_st
    p.act_st_name = ACT_ST_NAMES[pl.act_st]
    p.throw_invuln = pl.catch_muteki
    p.full_invuln = pl.muteki_time
    p.juggle = pl.combo_dm_air
    p.buff = pl.style_timer
    p.posX = pl.pos.x.v / 6553600.0
    p.posY = pl.pos.y.v / 6553600.0
    p.spdX = pl.speed.x.v / 6553600.0
    p.spdY = pl.speed.y.v / 6553600.0
    p.pushback = safe(function() return pl.vector_zuri.speed.v / 6553600.0 end)
    if inputInfo then
        p.input = safe(function() return inputInfo._InputNew.u32 end)
        p.input_side = safe(function() return inputInfo.InputSide end)
    end
    return p
end

local function read_frame()
    local gBattle = sdk.find_type_definition("gBattle")
    if not gBattle then return end
    local sRound = gBattle:get_field("Round"):get_data(nil)
    local sGame = gBattle:get_field("Game"):get_data(nil)
    if not sRound or not sGame then return end
    local fight_st = sGame.fight_st

    -- match over (fight_st 7): auto-save once as <replayid>.json, then reset for the next replay
    if fight_st == 7 then
        if autosave and not game_saved and frames_captured > 0 then
            read_replay_info()
            local id = replay.info.replay_id
            local name = (id and tostring(id) ~= "") and (tostring(id) .. ".json") or ("replay_" .. os.time() .. ".json")
            if save(name) then clear() end
            game_saved = true
        end
        return
    end
    if fight_st == 0 then              -- not in a fight (menus, loading)
        -- A replay left before its end (fight_st 7) never saves; drop its frames once we've been out
        -- of a fight for ~5 s, or they get glued onto the start of the next replay's capture.
        idle_frames = idle_frames + 1
        if idle_frames > 300 and frames_captured > 0 and not game_saved then
            clear(); last_saved = "discarded an unfinished replay"
        end
        return
    end
    idle_frames = 0
    game_saved = false

    local round_number, stage_timer = sRound.RoundNo, sGame.stage_timer
    if round_number == nil or stage_timer == nil then return end

    local cPlayer = gBattle:get_field("Player"):get_data(nil).mcPlayer
    local cTeam = gBattle:get_field("Team"):get_data(nil).mcTeam
    local latest = gBattle:get_field("Rollback"):get_data():GetLatestEngine()
    local e1 = latest.ActEngines[0]._Parent._Engine
    local e2 = latest.ActEngines[1]._Parent._Engine
    local fInput = safe(function() return gBattle:get_field("Input"):get_data(nil) end)
    local in1 = fInput and safe(function() return fInput.StorageData.Info[0] end)
    local in2 = fInput and safe(function() return fInput.StorageData.Info[1] end)

    if replay.info.p1_control == nil and in1 then
        replay.info.p1_control = safe(function() return in1.CommandType end)
        replay.info.p2_control = safe(function() return in2.CommandType end)
        replay.info.note = "control: CommandType per player (Classic/Modern); input: raw bits, decoded later"
    end

    -- read every frame: on the first fight frame the ids can still be from an earlier match
    do
        local sPlayer = gBattle:get_field("Player"):get_data(nil)
        replay.info.p1_char_id = safe(function() return sPlayer.mPlayerType[0].mValue end)
        replay.info.p2_char_id = safe(function() return sPlayer.mPlayerType[1].mValue end)
        replay.info.p1_char = CHARACTERS[replay.info.p1_char_id] or ("char_" .. tostring(replay.info.p1_char_id))
        replay.info.p2_char = CHARACTERS[replay.info.p2_char_id] or ("char_" .. tostring(replay.info.p2_char_id))
    end
    local round_timer = safe(function() return sRound.play_timer end)

    local p1 = read_player(0, cPlayer, cTeam, e1, in1)
    local p2 = read_player(1, cPlayer, cTeam, e2, in2)

    -- skip frames where nothing changed (paused)
    local key = table.concat({ tostring(round_number), tostring(stage_timer),
        tostring(p1.action_id), tostring(p1.action_frame), tostring(p2.action_id), tostring(p2.action_frame),
        tostring(p1.posX), tostring(p2.posX), tostring(p1.input), tostring(p2.input),
        tostring(p1.hp), tostring(p2.hp) }, ":")
    if key == last_key then return end
    last_key = key

    local idx = frames_captured + 1
    table.insert(replay.frames, { i = idx, round = round_number, round_timer = round_timer, stage_timer = stage_timer, fight_st = fight_st, p1 = p1, p2 = p2 })
    frames_captured = idx

    -- hit events: hitstun starts on a player, or the attacker's combo count goes up
    local players = { p1, p2 }
    for v = 1, 2 do
        local a = 3 - v
        local victim, attacker = players[v], players[a]
        local new_stun = (victim.hitstun or 0) > 0 and (last_hitstun[v] or 0) == 0
        local combo_up = (attacker.combo_count or 0) > (last_combo[a] or 0)
        if new_stun or combo_up then
            table.insert(replay.hits, {
                frame = idx, round = round_number, stage_timer = stage_timer,
                attacker = "p" .. a, victim = "p" .. v,
                attacker_action_id = attacker.action_id, attacker_action_frame = attacker.action_frame,
                attacker_combo_count = attacker.combo_count, attacker_combo_damage = attacker.combo_damage,
                victim_action_id = victim.action_id, victim_hp = victim.hp, victim_posY = victim.posY,
                victim_damage_info = dump_fields(safe(function() return cPlayer[v - 1].damage_info end)),
            })
            hits_captured = hits_captured + 1
        end
    end
    last_hitstun = { p1.hitstun or 0, p2.hitstun or 0 }
    last_combo = { p1.combo_count or 0, p2.combo_count or 0 }

    -- battle stats: store only the fields that changed
    local sStats = safe(function() return gBattle:get_field("Stats"):get_data(nil) end)
    if sStats then
        for pi = 1, 2 do
            local cur = dump_fields(safe(function() return sStats.Info[pi - 1] end))
            local diff, any = {}, false
            for k, val in pairs(cur) do
                if last_stats[pi][k] ~= val then diff[k] = val; any = true end
            end
            if any then
                table.insert(replay.stats, { frame = idx, round = round_number, stage_timer = stage_timer, player = "p" .. pi, changed = diff })
                last_stats[pi] = cur
            end
        end
    end

    -- charge state (charge characters): saved when it changes
    local storage = safe(function() return gBattle:get_field("Command"):get_data(nil).StorageData end)
    if storage then
        for pi = 1, 2 do
            local infos = safe(function() return storage.UserEngines[pi - 1].m_charge_infos end)
            if infos then
                local list = {}
                for ci, info in ipairs(to_list(infos)) do list[#list + 1] = dump_fields(info) end
                local parts = {}
                for _, d in ipairs(list) do parts[#parts + 1] = sig(d) end
                local s = table.concat(parts, "|")
                if s ~= last_charge[pi] then
                    last_charge[pi] = s
                    table.insert(replay.charge, { frame = idx, player = "p" .. pi, charges = list })
                end
            end
        end
    end

    -- projectiles (experimental): each work slot's numeric fields, saved when they change
    local works = capture_projectiles and safe(function() return gBattle:get_field("Work"):get_data(nil).Global_work end)
    if works then
        local n = 0
        for wi, w in ipairs(to_list(works)) do
            n = n + 1
            if n > 16 then break end
            local d = dump_fields(w)
            local s = sig(d)
            if s ~= last_proj[n] then
                last_proj[n] = s
                table.insert(replay.projectiles, { frame = idx, slot = n, fields = d })
            end
        end
    end
end

re.on_frame(function()
    if recording then
        local ok, err = pcall(read_frame)
        if not ok then last_error = tostring(err) end
    end
end)

-- UI lives under "Script Generated UI" in the REFramework menu (Insert), like Batch replays.
-- Recording runs in on_frame above whether or not the menu is open.
re.on_draw_ui(function()
    if not imgui.tree_node("Replay Capture v3.5") then return end
    local changed
    changed, autosave = imgui.checkbox("Auto-save <replayid>.json at match end", autosave)
    changed, capture_projectiles = imgui.checkbox("Record projectiles (experimental; untick if the replay stutters)", capture_projectiles)
    if imgui.button(recording and "Pause recording" or "Resume recording") then recording = not recording end
    imgui.same_line()
    if imgui.button("Clear Buffer") then clear() end
    imgui.text("Frames: " .. frames_captured .. "   Hits: " .. hits_captured .. "   Stat changes: " .. #replay.stats)
    if last_saved then imgui.text("Last saved: " .. last_saved) end
    if last_error then imgui.text("Last error: " .. last_error) end
    if imgui.tree_node("Manual save") then
        filename_changed, manual_filename = imgui.input_text("Filename", manual_filename)
        if imgui.button("Save now") then
            read_replay_info()
            save(manual_filename)
        end
        imgui.tree_pop()
    end
    imgui.tree_pop()
end)
