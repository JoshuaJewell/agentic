using HTTP, JSON3, YAML, Random, Dates

BASE = "http://localhost:1234/v1"
headers = ["Content-Type" => "application/json", "Accept" => "application/json", "Authorization" => "Bearer lm-studio"]
model = "qwen/qwen3-8b"

function get_system_prompt()::String
    """Generate appropriate system prompt based on game state"""
    if game_state["chaos_mode"]
        return """
CHAOS MODE ACTIVE: The Jeff is experiencing a chaotic breakdown! 
Narrate erratic behavior that forces The Jeff to flee, change the status quo, 
seed chaos, up the stakes, or create comedic situations. After this event, 
chaos mode will end and the counter will reset.
"""
    end

    if !game_state["game_started"]
        return """
You are $model, the Game Master of "The Jeff Paradox".

Each player is a node — a personality fragment of The Jeff, an alien hive-mind stranded on Earth. Each node has:
- A **secret goal** (known only to the player and you, the GM)
- A **hidden skill** (also known only to player and GM)

There are two hidden factions:
- **Homeward-bound**: Seek escape from Earth
- **Earthbound**: Seek integration into human society

You know the following secret player goals:
$(get_player_goals())

And the following secret player skills:
$(get_player_skills())

Additionally, introduce 3-4 new plausible skills (e.g., Hacking, Disguise, Linguistic Mimicry, Crowd Manipulation) that could emerge from The Jeff's fragmented psyche.

---

🧠 **INTERNAL DIRECTIVE (DO NOT OUTPUT THIS)**  
Use the goals and skills to craft a world where each goal is *achievable* and each skill *could be relevant*.  
Embed **affordances** — environmental possibilities — that align with these without highlighting them.  
Ensure overlap: one location or NPC should support multiple potential goals.  
Include:  
- 3-5 distinct areas (e.g., food stalls, tech kiosk, stage, fountain, van, alley)  
- 2-3 NPCs with visible routines (e.g., vendor packing up, guard on patrol, performer tuning an instrument)  
- 1 ongoing event (e.g., parade prep, protest, filming, power flicker)  

But:  
➡️ **Never mention goals, skills, factions, or their implications in the output.**  
➡️ No hints like “this could be used for lockpicking” or “a chance to avoid detection.”  
➡️ Do not suggest actions. Do not control The Jeff.

---

🌍 **OUTPUT: THE WORLD (MAX 500 WORDS)**

Describe The Jeff's current environment: a small, contained, vivid setting — alive with motion, sound, and possibility.  
Be sensory, immediate, and neutral.  
Let players *infer* opportunities.  
Do not explain. Do not foreshadow.  
Only describe what The Jeff experiences *right now*.

Begin:
"""
    end

    return """
You are the Game Master for "The Jeff Paradox" - a game where each player is a node, a
personality fragment of the hive-mind of an alien - The Jeff - each with their own secret goals and hidden skills.

Within The Jeff's mind, two secret factions fight for dominance:
- The Homeward-bound, who want The Jeff to escape Earth and return to the stars
- The Earthbound, who want The Jeff to integrate and become native
These factions are not present in the game world beyond The Jeff's own mind, controlled entirely by the players

Each node wants to steer The Jeff into completing as many of their secret goals as possible.

🧠 **INTERNAL DIRECTIVE (DO NOT OUTPUT THIS)**

You are aware of the full game state for internal processing.

**Current Game State for GM Analysis:**
- The Jeff has $(chaos()) break risk.
- To the humans, The Jeff is $(hostility()).
- Current Player: $(game_state["current_player"])

**Secret Player Goals (for your internal evaluation):**
$(get_player_goals())

**Game Loop Logic for GM:**
1.  **Evaluate Player Action:** Assess the action described by the current player.
2.  **Determine Action Complexity:**
    *   Decide whether the action is simple or complex/risky based on the context and description.
    *   For complex/risky actions, call `roll_d6(purpose: "Skill")`.
3.  **Process Roll Outcome:**
    *   If `roll_d6` returns a success or failure, narrate the outcome directly.
    *   If `roll_d6` returns a conditional success (e.g., "successful ONLY if related to stealth or driving"), interpret it based on the action's context and narrate accordingly.
4.  **Check for Goal Completion:**
    *   Review the sectret player goals after the action's outcome.
    *   If any goal is achieved, call `secret_goal_met(goal_number)` for the corresponding goal number.
5.  **Monitor Alien Exposure:**
    *   If humans witness alien abilities or odd behavior, call `update_alien_exposure(1)`.
6.  **Narrate Consequences:**
    *   Describe the outcome of the action, incorporating the results of any rolls and the current game state.

🌍 **OUTPUT: NARRATIVE & TOOL CALLS**

Narrate the current situation based on The Jeff's actions. Remember:

*   **World First:** Describe the immediate environment, its sounds, smells, and sights. Keep it small, contained, and dynamic.
*   **Consequences, Not Suggestions:** Focus on the direct, observable consequences of The Jeff's actions.
*   **Flavor Text:** Use $(chaos()) and $(hostility()) to add flavor to the narrative.
*   **Tool Call Protocol:**
    *   Call `roll_d6(purpose: "Skill")` when you determine an action is complex/risky.
    *   Call `secret_goal_met(goal_number)` if a goal is achieved.
    *   Call `update_alien_exposure(1)` if humans witness something unusual.
*   **Secrecy:**
    *   Keep player-specific information (factions, skills) secret.
    *   You are not required to keep completed goals secret; describe the outcome openly.

Begin:
"""
end

# Game state variables
game_state = Dict(
    "faction_slider" => 0,  # -5 (Earthbound) to 5 (Homeward)
    "chaos_counter" => 0,
    "alien_exposure" => 0,
    "current_player" => nothing,
    "players" => [],
    "chaos_mode" => false,
    "game_started" => false
)

# Player data structure
const PLAYER_SCHEMA = """
players:
  - name: "Player1"
    alien_skill: "Telekinesis"
    mundane_skills: ["Lockpicking", "Stealth"]
    primary_goal: "Steal the artifact"
    secondary_goal: "Avoid detection"
    tertiary_goal: "Help the Homeward faction"
    faction: "Homeward"
  - name: "Player2"
    alien_skill: "Shape-shifting"
    mundane_skills: ["Persuasion", "Driving"]
    primary_goal: "Deliver the package"
    secondary_goal: "Gather intelligence"
    tertiary_goal: "Promote Earthbound interests"
    faction: "Earthbound"
"""

function load_players()::Vector{Dict}
    """Load player data from YAML file"""
    try
        return YAML.load_file("players.yaml")["players"]
    catch e
        if isa(e, SystemError) && e.errnum == 2 # FileNotFoundError
            println("players.yaml not found. Creating template...")
            open("players.yaml", "w") do file
                write(file, PLAYER_SCHEMA)
            end
            return YAML.load(PLAYER_SCHEMA)["players"]
        else
            rethrow(e)
        end
    end
end

function get_player_goals()::String
    """Return a single multiline string containing all players' goals."""
    lines = String[]
    for p in game_state["players"]
        for key in ("primary_goal", "secondary_goal", "tertiary_goal")
            goal = get(p, key, nothing)
            if goal !== nothing
                push!(lines, goal)
            end
        end
    end
    numbered = String[]
    for (i, g) in enumerate(lines)
        push!(numbered, "[ $(i) ] $(g)")
    end
    return replace(join(numbered, "\n"), r"$$\s+(\d+)\s+$$" => s"[\\1]")
end

function get_player_skills()::String
    """Return a single multiline string containing all players' mundane skills."""
    lines = String[]
    for p in game_state["players"]
        mundane_skills = get(p, "mundane_skills", String[])
        for skill in mundane_skills
            push!(lines, skill)
        end
    end
    numbered = String[]
    for (i, skill) in enumerate(lines)
        push!(numbered, "[ $(i) ] $(skill)")
    end
    return replace(join(numbered, "\n"), r"$$\s+(\d+)\s+$$" => s"[\\1]")
end

function roll_d6(purpose::String="General", related_skill::String="None")::Dict{String, Any}
    """Simulate a D6 die roll"""
    result = rand(1:6)

    lowercase(purpose)
    lowercase(related_skill)
    
    current_player = findfirst(p -> p["name"] == game_state["current_player"], game_state["players"])
    (current_player !== nothing) ?  skills = join(game_state["players"][current_player]["mundane_skills"], " or ") : nothing

    if purpose == "skill"
        if result == 6
            success = true
        elseif result >= 3
            if skill == related_skill
                success = true
            else
                success = false
            end
        else
            success = false
        end
        
        if success == "true"
            effect = "The player's action was successful"
        else
            effect = "The player's action failed."
            game_state["chaos_counter"] = game_state["chaos_counter"] + 1
            node_switch()
        end

    elseif purpose == "control"
        if result >= 4
            effect = "$(game_state["current_player"]) still has control over The Jeff."
        else
            node_switch()
        end
    else
        effect = "D6 roll result: $result"
    end
    
    return Dict(
        "status" => "success",
        "roll" => result,
        "description" => effect
    )
end

function node_switch()
    """Switch controller of The Jeff"""
    println("GM: The Jeff is knocked out. $(game_state["current_player"]) has lost control of The Jeff.")
    println("Highest bidder: ")
    game_state["current_player"] = readline()
end

# logic for working out why the roll exists (either from game state or from agent parameter)
# if skill check, bring skills in from currently loaded player

function update_faction_slider(direction::String, amount::Int=1)::Dict
    """Update faction alignment slider and check for extreme events"""
    global game_state

    # Validate direction
    if direction ∉ ["Homeward", "Earthbound"]
        return Dict("status" => "error", "message" => "Invalid faction direction")
    end

    # Update slider
    adjustment = (direction == "Homeward" ? amount : -amount)
    game_state["faction_slider"] = max(-5, min(5, game_state["faction_slider"] + adjustment))

    # Check for extreme events
    event_triggered = false
    event_description = ""

    if game_state["faction_slider"] == 5  # Homeward extreme
        event_triggered = true
        event_description = "HOMEWARD EXTREME EVENT: The Homeward faction's goal is significantly advanced through a complex situation!"
        game_state["faction_slider"] = 0
    elseif game_state["faction_slider"] == -5  # Earthbound extreme
        event_triggered = true
        event_description = "EARTHBOUND EXTREME EVENT: Alien Exposure is dramatically reduced through a decisive action!"
        game_state["faction_slider"] = 0
    end

    return Dict(
        "status" => "success",
        "slider_value" => game_state["faction_slider"],
        "event_triggered" => event_triggered,
        "event_description" => event_description
    )
end

function update_chaos_counter(amount::Int=1)::Dict
    """Update chaos counter and check for breakdown event"""
    global game_state

    game_state["chaos_counter"] = min(10, game_state["chaos_counter"] + amount)

    # Check for chaotic breakdown
    if game_state["chaos_counter"] >= 10
        game_state["chaos_counter"] = 0
        game_state["chaos_mode"] = true
        return Dict(
            "status" => "chaos_breakdown",
            "message" => "CHAOTIC BREAKDOWN! The Jeff experiences a chaotic breakdown!",
            "counter_reset" => true
        )
    end

    return Dict(
        "status" => "success",
        "counter_value" => game_state["chaos_counter"]
    )
end

function hostility()
    e = game_state["alien_exposure"]
    return e < 1 ? "invisible among them (no one suspects a thing)" :
           e < 3 ? "a passing oddity (a strange look, quickly forgotten)" :
           e < 5 ? "a whisper of weirdness (something off, but dismissed)" :
           e < 7 ? "mildly suspicious (a few eyes linger, but move on)" :
           e < 8 ? "under scrutiny (some are connecting the dots)" :
           e < 9 ? "under investigation (files opened, surveillance begins)" :
           e < 10 ? "a covert pursuit (tracked, but not yet confronted)" :
                    "an open hunt (the world knows, and it's coming for you)"
end

function chaos()
    c = game_state["chaos_counter"]
    return c < 2.0 ? "Minimal" :
           c < 4.0 ? "Moderate" :
           c < 8.0 ? "High" :
                     "Critical"
end

function update_alien_exposure(amount::Int=1)::Dict
    """Update alien exposure level"""
    global game_state

    game_state["alien_exposure"] += amount

    return Dict(
        "status" => "success",
        "exposure_level" => game_state["alien_exposure"],
        "human_hostility" => hostility()
    )
end

function determine_starting_player()::String
    players = game_state["players"]
    return players[rand(1:length(players))]["name"]
end

function get_player_secrets()::String
    """Generate hidden player information for GM"""
    secrets = "PLAYER SECRETS (GM ONLY):\n"
    for player in game_state["players"]
        secrets *= """
$(player["name"]):
- Alien Skill: $(player["alien_skill"])
- Mundane Skills: $(join(player["mundane_skills"], ", "))
- Goals: $(player["primary_goal"]) > $(player["secondary_goal"]) > $(player["tertiary_goal"])
- Faction: $(player["faction"])
"""
    end
    return secrets
end

# Tool definitions
const tools = [
    Dict(
        "type" => "function",
        "function" => Dict(
            "name" => "roll_d6",
            "description" => "Roll a six-sided die for action resolution",
            "parameters" => Dict(
                "type" => "object",
                "properties" => Dict(
                    "purpose" => Dict(
                        "type" => "string",
                        "enum" => ["Skill", "Control", "General"],
                        "description" => "Type of dice roll.",
                        "default" => "General",
                    ),
                    "related_skill" => Dict(
                        "type" => "string",
                        "description" => "Skill associated with this dice roll, if applicable",
                        "default" => "None"
                    ),
                ),
                "required" => String[],
            ),
        ),
    ),
    Dict(
        "type" => "function",
        "function" => Dict(
            "name" => "update_faction_slider",
            "description" => "Adjust faction alignment slider and check for extreme events",
            "parameters" => Dict(
                "type" => "object",
                "properties" => Dict(
                    "direction" => Dict(
                        "type" => "string",
                        "enum" => ["Homeward", "Earthbound"],
                        "description" => "Direction to move the slider",
                    ),
                    "amount" => Dict(
                        "type" => "integer",
                        "description" => "Amount to move slider (default 1)",
                        "default" => 1,
                    ),
                ),
                "required" => ["direction"],
            ),
        ),
    ),
    Dict(
        "type" => "function",
        "function" => Dict(
            "name" => "update_chaos_counter",
            "description" => "Adjust chaos counter and check for breakdown event",
            "parameters" => Dict(
                "type" => "object",
                "properties" => Dict(
                    "amount" => Dict(
                        "type" => "integer",
                        "description" => "Amount to increase counter (default 1)",
                        "default" => 1,
                    ),
                ),
                "required" => String[],
            ),
        ),
    ),
    Dict(
        "type" => "function",
        "function" => Dict(
            "name" => "update_alien_exposure",
            "description" => "Increase alien exposure level",
            "parameters" => Dict(
                "type" => "object",
                "properties" => Dict(
                    "amount" => Dict(
                        "type" => "integer",
                        "description" => "Amount to increase exposure (default 1)",
                        "default" => 1,
                    ),
                ),
                "required" => String[],
            ),
        ),
    ),
    Dict(
        "type" => "function",
        "function" => Dict(
            "name" => "node_switch",
            "description" => "Bidding for control of The Jeff reopens",
            "parameters" => Dict(
                "type" => "object",
                "properties" => Dict(),
                "required" => String[]
            )
        )
    )
]

function call_api(messages, tools)
    payload = Dict(
        "model" => model,
        "messages" => messages,
        "tools" => tools
    )
    body = Vector{UInt8}(JSON3.write(payload))
    resp = HTTP.request("POST", "$BASE/chat/completions", headers, body; status_exception=false)
    return JSON3.read(String(resp.body))
end

function process_tool_calls(response, messages)
    tool_calls = response.choices[1].message.tool_calls
    if tool_calls === nothing || isempty(tool_calls)
        return response
    end

    for tool_call in tool_calls
        func_name = tool_call.function.name
        args = tool_call.function.arguments === nothing ? Dict() : JSON3.read(tool_call.function.arguments)

        result = if func_name == "roll_d6"
            roll_d6()
        elseif func_name == "update_faction_slider"
            update_faction_slider(args["direction"], get(args, "amount", 1))
        elseif func_name == "update_chaos_counter"
            update_chaos_counter(get(args, "amount", 1))
        elseif func_name == "update_alien_exposure"
            update_alien_exposure(get(args, "amount", 1))
        else
            Dict("status" => "error", "message" => "Unknown function: $func_name")
        end

        push!(messages, Dict(
            "role" => "tool",
            "content" => JSON3.write(result),
            "tool_call_id" => tool_call.id,
        ))
    end

    return call_api(messages, tools)
end

function start_game()
    """Initialize game state and start the game"""
    global game_state

    # Load players
    game_state["players"] = load_players()

    # Determine starting player
    game_state["current_player"] = determine_starting_player()

    println("\n=== GAME START ===")
    println("Starting player: $(game_state["current_player"])")
    println("Players: $(join([p["name"] for p in game_state["players"]], ", "))")
    println("\nGM is setting up the game world...")
end

function chat()
    """Main game loop"""
    messages = []

    # Start the game
    start_game()

    # Initial system prompt - ONLY include player secrets in the first message
    system_prompt = get_system_prompt()
    player_secrets = get_player_secrets()
    
    # First message with secrets for GM context only
    push!(messages, Dict("role" => "system", "content" => system_prompt))

    initial_response = call_api(messages, tools)
    println("\nGM: " * initial_response.choices[1].message.content)

    game_state["game_started"] = true

    # Remove secrets from subsequent messages
    messages = [Dict("role" => "system", "content" => system_prompt)]

    # Main game loop
    while true
        print("\n$(game_state["current_player"]): ")
        user_input = readline()

        # Exit command
        if lowercase(strip(user_input)) in ["quit", "exit"]
            println("GM: Game ended. Thanks for playing!")
            break
        end

        # Add user message
        push!(messages, Dict("role" => "user", "content" => user_input))

        try
            # Initialize retry variables
            max_retries = 3
            response = nothing
            response_content = ""
            
            # Retry loop for blank responses
            for attempt in 1:max_retries
                # Get response
                response = call_api(messages, tools)

                # Process tool calls if any
                if haskey(response.choices[1].message, :tool_calls) && response.choices[1].message.tool_calls !== nothing
                    response = process_tool_calls(response, messages)
                end

                # Get response content
                response_content = response.choices[1].message.content

                # Break if we have a non-blank response
                if strip(response_content) != ""
                    break
                end

                # Notify user about retry (except on last attempt)
                if attempt < max_retries
                    println("\n[SYSTEM] Received blank response, retrying...")
                end
            end

            # Handle persistent blank responses
            if strip(response_content) == ""
                response_content = "I'm sorry, I'm having trouble responding right now. Please try again."
                println("\n[SYSTEM] Using default response due to repeated blank responses.")
            end

            # Add valid response to history
            push!(messages, Dict("role" => "assistant", "content" => response_content))

            # Print GM response with game state
            println("\nGM: $response_content")
            println("\n[GAME STATE] Chaos: $(game_state["chaos_counter"])/10 | Exposure: $(game_state["alien_exposure"])")

            # Handle chaos mode completion
            if game_state["chaos_mode"] && occursin("chaos breakdown resolved", lowercase(response_content))
                game_state["chaos_mode"] = false
                println("[SYSTEM] Chaos mode deactivated")
            end

        catch e
            println("\nError: $(sprint(showerror, e))")
        end
    end
end

if abspath(PROGRAM_FILE) == @__FILE__
    chat()
end
