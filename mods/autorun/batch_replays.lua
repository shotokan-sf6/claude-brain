-- batch_replays.lua (REFramework, Street Fighter 6)
-- Plays a queue of replays by replay ID, one at a time, driven by batch_record.py.
-- Ideas from rkaganda/sf6_replays_data (flow_control.lua / auto_replay_capture.lua):
--   * the current screen is read from app.UIFlowManager (top flow name)
--   * the replay-ID search is submitted directly with TextInputDialogWidget:InvokeResultEvent
--   * menu keys are injected by hooking app.InputDeviceStateKeyboard.GetDigital
-- Runs next to capture_replay.lua, which saves reframework/data/<replayid>.json at match end.
--
-- Files (reframework/data/sf6_batch/):
--   command.json  written by batch_record.py: {"seq": 3, "action": "play", "replay_id": "ABC123XYZ"}
--                 action "idle" stops all key presses.
--   status.json   written here every 10 frames: seq, phase, top_flow, fight_st, replay_id, note
--   config.json   optional overrides for the key sequences below (same shape as DEFAULT_CFG)
--   flows.json    every top flow (screen) name seen, in order (for calibrating the sequences)
--
-- Phases: idle -> to_search -> searching -> opening -> playing -> ending -> done (or error)
--
-- Navigation is driven by the screen on top (see flows.json), not by blind key sequences:
-- each known screen has a short key sequence (cfg.nav), and unknown screens get no keys at all,
-- so the script can't wander off to the title screen. After a replay SF6 restores the old
-- CFN > Replays > search result screen, so the next ID starts with one Escape from there.

local DIR = "sf6_batch/"
local SEARCH_FLOW  = "app.UICFNReplayTopTabSearchChildSearchId.FlowParam"
local RESULT_FLOW  = "app.UICFNReplaySearchResult.FlowParam"
local INFO_FLOW    = "app.UICFNReplayInfoOnline.FlowParam"
local END_MENU     = "app.esports.UIReplayResultMenu.Param"
local MSGBOX       = "app.UIFlowDialog.MessageBoxParam"
local CFN_TOP      = "app.UICFNTop.FlowParam"
local TEXT_BOX     = "app.UIWidget.BaseParam_CreateByContainer"   -- the ID text box (also other widgets)

-- A sequence is a list of {key, wait}: the key is pressed once (one frame), then the script waits
-- `wait` ticks of 1/60 s ("" = wait only).
-- Key names are via.hid.KeyboardKey names (F, S, Escape, Return ...). F confirms, S moves down.
local DEFAULT_CFG = {
    -- per-screen steps toward the Search-by-ID box while looking for it
    nav = {
        -- old results (where SF6 returns after a replay) -> back to Keyword Search
        [RESULT_FLOW] = { {"", 20}, {"Escape", 3}, {"", 30} },
        [INFO_FLOW]   = { {"", 20}, {"Escape", 3}, {"", 40} },          -- SF6 reopens this after a replay
        -- Keyword Search opens with the cursor on "Search by player name": up once wraps round to
        -- "Search by Replay ID", then confirm. The screen fades in for about a second and drops keys
        -- pressed during the fade, hence the wait. The menu also follows the mouse: keep the pointer
        -- off the game window or this lands on the wrong row.
        [SEARCH_FLOW] = { {"", 30}, {"W", 3}, {"", 20}, {"F", 3}, {"", 40} },
        [CFN_TOP]     = { {"", 20}, {"S", 3}, {"", 15}, {"S", 3}, {"", 15}, {"F", 3}, {"", 60} },  -- calibrate
        [MSGBOX]      = { {"", 30}, {"Escape", 3}, {"", 40} },          -- cancel a stray dialog
    },
    -- on the search result list: open the first result (fallback scrolls down once first)
    on_results     = { {"", 30}, {"F", 3}, {"", 30} },
    on_results_alt = { {"", 10}, {"S", 3}, {"", 15}, {"F", 3}, {"", 30} },
    -- on the replay info screen: start watching
    on_info        = { {"", 30}, {"F", 3}, {"", 30} },
    -- on the result menu after a replay that played to the end: End Replay is one down, then confirm
    on_end         = { {"", 30}, {"S", 3}, {"", 15}, {"F", 3}, {"", 60} },
    on_end_retry   = { {"", 10}, {"F", 3}, {"", 60} },   -- cursor is already on End Replay
    settle_frames  = 45,    -- a screen must stay on top this long before keys are pressed on it
    settle_screen  = { [INFO_FLOW] = 150, [SEARCH_FLOW] = 60 },   -- SF6 shows the info screen briefly while restoring after a replay
    retry_frames   = 240,   -- repeat a screen's sequence if the screen hasn't changed after this
    timeout_frames = 5400,  -- give up on a phase after 90 s
}

local cfg = DEFAULT_CFG
do
    local ok, user = pcall(json.load_file, DIR .. "config.json")
    if ok and type(user) == "table" then
        for k, v in pairs(user) do
            if k == "nav" and type(v) == "table" then for sk, sv in pairs(v) do cfg.nav[sk] = sv end
            else cfg[k] = v end
        end
    end
end

-- ---------------------------------------------------------------- helpers
local function enum(typename)
    local t = sdk.find_type_definition(typename); local e = {}
    if not t then return e end
    for _, f in ipairs(t:get_fields()) do if f:is_static() then
        local ok, v = pcall(function() return f:get_data(nil) end)
        if ok and v ~= nil then e[v] = f:get_name() end end end
    return e
end
local KEYS = enum("via.hid.KeyboardKey")

-- All waits are in "ticks" of 1/60 s of real time. Menus can render far faster than 60 fps,
-- so counting rendered frames made every wait much shorter than intended.
local APP_T = sdk.find_type_definition("via.Application")
local function now_seconds()
    local ok, t = pcall(function()
        return sdk.call_native_func(sdk.get_native_singleton("via.Application"), APP_T, "get_UpTimeSecond")
    end)
    if ok and type(t) == "number" then return t end
    return os.clock()
end
local last_clock = nil
local function elapsed_ticks()
    local t = now_seconds()
    local d = last_clock and (t - last_clock) * 60 or 1
    last_clock = t
    if d < 0 or d > 30 then d = 1 end   -- clock jump or a long hitch: count one tick
    return d
end

local state = { seq = -1, phase = "idle", replay_id = nil, note = "", top_flow = "", fight_st = 0, msg = "",
                phase_frames = 0, dt = 1, seq_steps = nil, seq_name = nil, seq_pos = 0, seq_frame = 0, seq_runs = 0, last_run = 0,
                last_flow_change = 0, frame = 0, saw_fight = false, saw_msg = false }
local held = {}            -- key name -> true while a sequence step holds it
local update_frame = 0
local status_timer = 0
local seen_flows = {}

local function log_flow(name)
    if seen_flows[name] then return end
    seen_flows[name] = true
    local ok, lines = pcall(json.load_file, DIR .. "flows.json")
    lines = (ok and type(lines) == "table") and lines or {}
    table.insert(lines, name); json.dump_file(DIR .. "flows.json", lines)
end

local function set_phase(p, note)
    if state.phase ~= p then state.phase = p; state.phase_frames = 0; state.seq_name = nil; state.seq_runs = 0 end
    if note then state.note = note end
end

-- start a key sequence (by name, for logging) unless one is already running
local function run_seq(name, steps)
    if state.seq_name ~= nil or not steps then return end
    state.seq_name = name; state.seq_steps = steps; state.seq_pos = 1; state.seq_frame = 0; state.seq_pressed = false
    state.seq_runs = state.seq_runs + 1
end

local function step_seq()
    held = {}
    local st = state.seq_name and state.seq_steps[state.seq_pos]
    if not st then state.seq_name = nil; return end   -- finished
    -- a key step presses its key on the step's first frame only; the rest of the step is a wait
    if st[1] ~= "" and not state.seq_pressed then held[st[1]] = true; state.seq_pressed = true end
    state.seq_frame = state.seq_frame + state.dt
    if state.seq_frame >= st[2] then state.seq_pos = state.seq_pos + 1; state.seq_frame = 0; state.seq_pressed = false end
end

-- run the sequence for this screen once it has settled, and again if the screen is stuck.
-- (After a replay SF6 rebuilds CFN top > search result > replay info in about a second;
-- pressing keys before that settles sends them to the wrong screen.)
local function drive(name, steps, no_settle)
    if state.seq_name then return end
    local settle = (cfg.settle_screen and cfg.settle_screen[state.top_flow]) or cfg.settle_frames
    if not no_settle and state.frame - state.last_flow_change < settle then return end
    if state.seq_runs == 0 or state.frame - state.last_run > cfg.retry_frames then
        state.last_run = state.frame
        run_seq(name, steps)
    end
end

local function flow_items()
    local m = sdk.get_managed_singleton("app.UIFlowManager"); if not m then return nil end
    local h = m._Handles; return h and h._items
end

local function param_of(it)
    local ok, p = pcall(function() return it:get_field("<Param>k__BackingField") end)
    return ok and p or nil
end

local function top_flow_name(items)
    local ok, n = pcall(function() return param_of(items[0]):get_type_definition():get_full_name() end)
    return ok and n or ""
end

local function find_flow(items, name)
    for i = 0, #items - 1 do
        local it = items[i]; if it == nil then return nil end
        local p = param_of(it)
        if p and p:get_type_definition():get_full_name() == name then return p end
    end
end

-- the ID text box widget, once the search screen has opened it
local function search_widget(items)
    local f = find_flow(items, SEARCH_FLOW); if not f then return nil end
    local ok, w = pcall(function() return f:get_field("<TextInputDialogWidget>k__BackingField") end)
    return ok and w or nil
end

local function invoke_search(w, text)
    return pcall(function() w:InvokeResultEvent(text) end)
end

-- best effort: the strings inside a dialog's param (message text or message id), for the log
local function strings_of(obj, depth, out)
    out = out or {}
    if not obj or depth < 0 or #out >= 6 then return out end
    local td = obj:get_type_definition()
    while td do
        for _, f in ipairs(td:get_fields()) do
            if not f:is_static() and #out < 6 then
                local ok, v = pcall(function() return obj:get_field(f:get_name()) end)
                if ok and v ~= nil then
                    local tn = f:get_type():get_full_name()
                    if type(v) == "string" and v ~= "" then
                        table.insert(out, f:get_name() .. "=" .. v:sub(1, 160))
                    elseif tn == "System.Guid" or (type(v) == "number" and f:get_name():lower():find("message")) then
                        table.insert(out, f:get_name() .. "=" .. tostring(v))
                    elseif type(v) == "userdata" and f:get_name():lower():find("mess") then
                        strings_of(v, depth - 1, out)
                    end
                end
            end
        end
        td = td:get_parent_type()
        if td and td:get_full_name():find("^System%.") then break end
    end
    return out
end

local function fight_state()
    local ok, v = pcall(function() return sdk.find_type_definition("gBattle"):get_field("Game"):get_data(nil).fight_st end)
    return ok and v or 0
end

local function capture_saved(id)
    local ok, d = pcall(json.load_file, id .. ".json")
    return ok and d ~= nil
end

-- ---------------------------------------------------------------- main loop
local function read_command()
    local ok, c = pcall(json.load_file, DIR .. "command.json")
    if not ok or type(c) ~= "table" or c.seq == nil or c.seq == state.seq then return end
    state.seq = c.seq
    state.msg = ""; state.saw_msg = false
    if c.action == "play" and c.replay_id then
        state.replay_id = c.replay_id; state.saw_fight = false; state.end_tried = false; set_phase("to_search", "new job")
    else
        state.replay_id = nil; set_phase("idle", "idle"); held = {}
    end
end

local function tick()
    state.dt = elapsed_ticks()
    state.frame = state.frame + state.dt; state.phase_frames = state.phase_frames + state.dt
    state.cmd_timer = (state.cmd_timer or 0) + state.dt
    if state.cmd_timer >= 30 then state.cmd_timer = 0; read_command() end
    local items = flow_items(); if not items then return end
    local top = top_flow_name(items)
    if top ~= state.top_flow then
        state.top_flow = top; state.last_flow_change = state.frame; state.seq_runs = 0; log_flow(top)
        if top == MSGBOX then
            local p = find_flow(items, MSGBOX)
            local ok, s = pcall(strings_of, p, 1)
            state.msg = (ok and #s > 0) and table.concat(s, "; ") or "(dialog, text not readable)"
        end
    end
    state.fight_st = fight_state()
    local p = state.phase

    if p == "idle" or p == "done" or p == "error" then held = {}; return end
    if p ~= "playing" and p ~= "ending" and state.phase_frames > cfg.timeout_frames then
        set_phase("error", "timed out in phase " .. p .. " on screen " .. top); held = {}; return end

    if p == "to_search" then
        -- only submit into a text box we just opened: the search screen keeps the old widget
        -- in its stack after a search, and submitting into that one fails ("No such replays found")
        local w = (top == TEXT_BOX and state.seq_name == nil) and search_widget(items) or nil
        if w and invoke_search(w, state.replay_id) then
            state.seq_name = nil; set_phase("searching", "search submitted")
        elseif cfg.nav[top] then
            drive("nav " .. top, cfg.nav[top])
        elseif state.phase_frames > 600 and state.frame - state.last_flow_change > 600 then
            set_phase("error", "don't know how to reach Search by Replay ID from " .. top ..
                ". Open CFN > Replays > Search by ID by hand and run it again.")
        end
    elseif p == "searching" or p == "opening" then
        if state.fight_st ~= 0 then set_phase("playing", "replay started"); held = {}; return end
        if top == MSGBOX then state.saw_msg = true end
        if top == RESULT_FLOW then
            if p == "searching" then set_phase("opening", "result found") end
            drive("on_results", state.seq_runs >= 1 and cfg.on_results_alt or cfg.on_results)
        elseif top == INFO_FLOW then
            if p == "searching" then set_phase("opening", "info screen") end
            drive("on_info", cfg.on_info)
        elseif top == SEARCH_FLOW and state.saw_msg and state.frame - state.last_flow_change > 60 then
            set_phase("error", "search failed: " .. state.msg)
        end
    elseif p == "playing" then
        held = {}
        if state.fight_st ~= 0 then state.saw_fight = true end
        if find_flow(items, END_MENU) or (state.fight_st == 7 and capture_saved(state.replay_id)) then
            set_phase("ending", capture_saved(state.replay_id) and "match over, capture saved" or "match over, no capture yet")
        end
        if state.phase_frames > 60 * 60 * 15 then set_phase("error", "replay ran over 15 minutes") end
    elseif p == "ending" then
        -- the Play Again / End Replay menu stays open while UIEnjoy takes the top spot,
        -- so look for it anywhere in the stack, and don't wait for it to settle
        local menu_open = find_flow(items, END_MENU) ~= nil
        if menu_open and not state.seq_name and (not state.end_tried or state.frame - state.last_run > cfg.retry_frames) then
            state.last_run = state.frame
            run_seq("on_end", state.end_tried and cfg.on_end_retry or cfg.on_end)
            state.end_tried = true
        end
        if state.fight_st == 0 and not menu_open and state.phase_frames > 60 then
            set_phase("done", "replay closed" .. (capture_saved(state.replay_id) and "" or " (no capture json)"))
        end
        if state.phase_frames > cfg.timeout_frames then set_phase("done", "end menu not confirmed (check the screen)") end
    end
    step_seq()
end

local function write_status()
    json.dump_file(DIR .. "status.json", { seq = state.seq, phase = state.phase, replay_id = state.replay_id, note = state.note, msg = state.msg,
        top_flow = state.top_flow, fight_st = state.fight_st, held = held, frame = math.floor(state.frame) })
end

-- ---------------------------------------------------------------- key injection
-- Marks a held key as pressed when the game asks the keyboard for it (same trick as rkaganda's flow_control.lua).
-- Same scheme as rkaganda's flow_control.lua: a press is ONE rendered frame. On that frame the
-- keyboard state gets Flags 11 + TriggerFrame (press_held), and until the next frame the
-- GetDigital hook reports the key as down (Flags only). Holding a key for several frames made
-- the game count one press per frame at ~120 fps, so one W moved the cursor several rows.
local function inject(key, from_hook)
    if key and held[KEYS[key.Value]] then
        key.Flags = 11
        if not from_hook then key.TriggerFrame = update_frame end
    end
end
-- also press held keys directly in the keyboard state each frame (flow_control.lua does both)
local function press_held()
    local im = sdk.get_managed_singleton("app.InputManager"); if not im then return end
    local ks = im._State and im._State._Keyboard and im._State._Keyboard._Keys; if not ks then return end
    for _, key in pairs(ks) do if key then inject(key) end end
end

re.on_frame(function()
    local ok, err = pcall(tick)
    if next(held) then pcall(press_held) end
    if not ok then state.note = "lua error: " .. tostring(err) end
    status_timer = status_timer + (state.dt or 1)
    if status_timer >= 10 then status_timer = 0; pcall(write_status) end
end)

re.on_draw_ui(function()
    if imgui.tree_node("Batch replays") then
        imgui.text("Phase: " .. state.phase .. "  ID: " .. tostring(state.replay_id))
        imgui.text(string.format("Frame time: %.1f ms", (state.dt or 1) * 1000 / 60))
        imgui.text("Screen: " .. state.top_flow)
        imgui.text("Note: " .. state.note)
        if state.msg ~= "" then imgui.text("Dialog: " .. state.msg) end
        if imgui.button("Stop") then set_phase("idle", "stopped from the REFramework menu"); held = {} end
        imgui.tree_pop()
    end
end)

local kb = sdk.find_type_definition("app.InputDeviceStateKeyboard")
if kb then
    sdk.hook(kb:get_method("GetDigital"), function(args) end, function(retval)
        local addr = sdk.to_int64(retval)
        if addr ~= 0 then pcall(inject, sdk.to_managed_object(retval), true) end
        return retval
    end)
end
local ist = sdk.find_type_definition("app.InputState")
if ist then
    sdk.hook(ist:get_method("Update"), function(args) update_frame = sdk.to_int64(args[4]) end, function(r) return r end)
end
