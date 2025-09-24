import yaml
import random
import json
from openai import OpenAI
from typing import Dict, List, Optional

# Initialize OpenAI client for LM Studio
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
model = "qwen/qwen3-8b"

# Game state variables
game_state = {
    "faction_slider": 0,  # -5 (Earthbound) to 5 (Homeward)
    "chaos_counter": 0,
    "alien_exposure": 0,
    "current_player": None,
    "players": [],
    "chaos_mode": False,
    "game_started": False
}

# Player data structure
PLAYER_SCHEMA = """
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

def load_players() -> List[Dict]:
    """Load player data from YAML file"""
    try:
        with open("players.yaml", "r") as file:
            return yaml.safe_load(file)["players"]
    except FileNotFoundError:
        print("players.yaml not found. Creating template...")
        with open("players.yaml", "w") as file:
            file.write(PLAYER_SCHEMA)
        return yaml.safe_load(PLAYER_SCHEMA)["players"]

def roll_d6()::Dict{String, Any}
    """Simulate a D6 die roll"""
    result = rand(1:6)
    return Dict(
        "status" => "success",
        "roll" => result,
        "description" => "D6 roll result: $result"
    )
end

def update_faction_slider(direction: str, amount: int = 1) -> Dict:
    """Update faction alignment slider and check for extreme events"""
    global game_state
    
    # Validate direction
    if direction not in ["Homeward", "Earthbound"]:
        return {"status": "error", "message": "Invalid faction direction"}
    
    # Update slider
    adjustment = amount if direction == "Homeward" else -amount
    game_state["faction_slider"] = max(-5, min(5, game_state["faction_slider"] + adjustment))
    
    # Check for extreme events
    event_triggered = False
    event_description = ""
    
    if game_state["faction_slider"] == 5:  # Homeward extreme
        event_triggered = True
        event_description = "HOMEWARD EXTREME EVENT: The Homeward faction's goal is significantly advanced through a complex situation!"
        game_state["faction_slider"] = 0
    elif game_state["faction_slider"] == -5:  # Earthbound extreme
        event_triggered = True
        event_description = "EARTHBOUND EXTREME EVENT: Alien Exposure is dramatically reduced through a decisive action!"
        game_state["faction_slider"] = 0
    
    return {
        "status": "success",
        "slider_value": game_state["faction_slider"],
        "event_triggered": event_triggered,
        "event_description": event_description
    }

def update_chaos_counter(amount: int = 1) -> Dict:
    """Update chaos counter and check for breakdown event"""
    global game_state
    
    game_state["chaos_counter"] = min(10, game_state["chaos_counter"] + amount)
    
    # Check for chaotic breakdown
    if game_state["chaos_counter"] >= 10:
        game_state["chaos_counter"] = 0
        game_state["chaos_mode"] = True
        return {
            "status": "chaos_breakdown",
            "message": "CHAOTIC BREAKDOWN! The Jeff experiences a chaotic breakdown!",
            "counter_reset": True
        }
    
    return {
        "status": "success",
        "counter_value": game_state["chaos_counter"]
    }

def update_alien_exposure(amount: int = 1) -> Dict:
    """Update alien exposure level"""
    global game_state
    
    game_state["alien_exposure"] += amount
    hostility = "Minimal" if game_state["alien_exposure"] < 3 else \
                "Moderate" if game_state["alien_exposure"] < 6 else \
                "High" if game_state["alien_exposure"] < 9 else "Extreme"
    
    return {
        "status": "success",
        "exposure_level": game_state["alien_exposure"],
        "human_hostility": hostility
    }

def determine_starting_player() -> str:
    """Determine starting player through D6 rolls"""
    rolls = []
    for player in game_state["players"]:
        roll = random.randint(1, 6)
        rolls.append((player["name"], roll))
        print(f"{player['name']} rolled: {roll}")
    
    # Find highest roll
    rolls.sort(key=lambda x: x[1], reverse=True)
    return rolls[0][0]

def get_system_prompt() -> str:
    """Generate appropriate system prompt based on game state"""
    base_prompt = f"""You are the Game Master for "The Jeff" - a game where players control an alien entity.
    
Current Game State:
- Faction Alignment: {game_state['faction_slider']} (-5=Earthbound, 5=Homeward)
- Chaos Counter: {game_state['chaos_counter']}/10
- Alien Exposure: {game_state['alien_exposure']} (Human Hostility: 
{'Minimal' if game_state['alien_exposure'] < 3 else 'Moderate' if game_state['alien_exposure'] < 6 else 'High' if game_state['alien_exposure'] < 9 else 'Extreme'})
- Current Player: {game_state['current_player'] or 'None'}
"""

    if game_state["chaos_mode"]:
        return base_prompt + """
CHAOS MODE ACTIVE: The Jeff is experiencing a chaotic breakdown! 
Narrate erratic behavior that forces The Jeff to flee, change the status quo, 
seed chaos, up the stakes, or create comedic situations. After this event, 
chaos mode will end and the counter will reset.
"""
    
    if not game_state["game_started"]:
        return base_prompt + """
GAME START: Describe The Jeff's current situation, environment, and basic information. 
Introduce the setting as a tightly packed playground (busy street, shopping center, 
small festival, etc.) with multiple paths to achieve goals. Include events and 
distractions (parade, TV filming, protest) and NPCs with their own goals and movement 
patterns (vendor packing up, patrolling guard, mayor giving speech).
"""
    
    return base_prompt + """
GAME LOOP: Narrate the current situation based on player actions. Remember:
- Keep the world small and immediate
- Create multiple paths to achieve goals
- Overlap player goals when possible
- Include dynamic events and NPCs
- For simple actions (walking, talking) no roll is needed
- For complex actions, call roll_d6 tool
- After failed actions or completed goals, request bidding for next player
"""

def get_player_secrets() -> str:
    """Generate hidden player information for GM"""
    secrets = "PLAYER SECRETS (GM ONLY):\n"
    for player in game_state["players"]:
        secrets += f"""
{player['name']}:
- Alien Skill: {player['alien_skill']}
- Mundane Skills: {', '.join(player['mundane_skills'])}
- Goals: {player['primary_goal']} > {player['secondary_goal']} > {player['tertiary_goal']}
- Faction: {player['faction']}
"""
    return secrets

# Tool definitions
tools = [
    {
        "type": "function",
        "function": {
            "name": "roll_d6",
            "description": "Roll a six-sided die for action resolution",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_faction_slider",
            "description": "Adjust faction alignment slider and check for extreme events",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["Homeward", "Earthbound"],
                        "description": "Direction to move the slider",
                    },
                    "amount": {
                        "type": "integer",
                        "description": "Amount to move slider (default 1)",
                        "default": 1,
                    },
                },
                "required": ["direction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_chaos_counter",
            "description": "Adjust chaos counter and check for breakdown event",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "integer",
                        "description": "Amount to increase counter (default 1)",
                        "default": 1,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_alien_exposure",
            "description": "Increase alien exposure level",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "integer",
                        "description": "Amount to increase exposure (default 1)",
                        "default": 1,
                    },
                },
                "required": [],
            },
        },
    },
]

def process_tool_calls(response, messages):
    """Process tool calls and update game state"""
    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        return response
    
    # Add assistant message with tool calls
    assistant_message = {
        "role": "assistant",
        "tool_calls": [
            {
                "id": tool_call.id,
                "type": tool_call.type,
                "function": tool_call.function,
            }
            for tool_call in tool_calls
        ],
    }
    messages.append(assistant_message)
    
    # Process each tool call
    for tool_call in tool_calls:
        func_name = tool_call.function.name
        args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
        
        # Execute the appropriate function
        if func_name == "roll_d6":
            result = roll_d6()
        elif func_name == "update_faction_slider":
            result = update_faction_slider(args.get("direction"), args.get("amount", 1))
        elif func_name == "update_chaos_counter":
            result = update_chaos_counter(args.get("amount", 1))
        elif func_name == "update_alien_exposure":
            result = update_alien_exposure(args.get("amount", 1))
        else:
            continue
        
        # Add tool result to messages
        messages.append({
            "role": "tool",
            "content": json.dumps(result),
            "tool_call_id": tool_call.id,
        })
    
    # Get final response after tool calls
    return client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
    )

def start_game():
    """Initialize game state and start the game"""
    global game_state
    
    # Load players
    game_state["players"] = load_players()
    
    # Determine starting player
    game_state["current_player"] = determine_starting_player()
    game_state["game_started"] = True
    
    print(f"\n=== GAME START ===")
    print(f"Starting player: {game_state['current_player']}")
    print(f"Players: {', '.join(p['name'] for p in game_state['players'])}")
    print("\nGM is setting up the game world...")

def chat():
    """Main game loop"""
    messages = []
    
    # Start the game
    start_game()
    
    # Initial system prompt
    system_prompt = get_system_prompt() + "\n\n" + get_player_secrets()
    messages.append({"role": "system", "content": system_prompt})
    
    print("\nGM: " + client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
    ).choices[0].message.content)
    
    # Main game loop
    while True:
        user_input = input(f"\n{current_player}: ").strip()
        
        # Exit command
        if user_input.lower() in ["quit", "exit"]:
            print("GM: Game ended. Thanks for playing!")
            break
        
        # Add user message
        messages.append({"role": "user", "content": user_input})
        
        try:
            # Get response
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
            )
            
            # Process tool calls if any
            if response.choices[0].message.tool_calls:
                response = process_tool_calls(response, messages)
            
            # Get response content
            response_content = response.choices[0].message.content
            messages.append({"role": "assistant", "content": response_content})
            
            # Print GM response with game state
            print(f"\nGM: {response_content}")
            print(f"\n[GAME STATE] Faction: {game_state['faction_slider']} | Chaos: {game_state['chaos_counter']}/10 | Exposure: {game_state['alien_exposure']}")
            
            # Handle chaos mode completion
            if game_state["chaos_mode"] and "chaos breakdown resolved" in response_content.lower():
                game_state["chaos_mode"] = False
                print("[SYSTEM] Chaos mode deactivated")
            
        except Exception as e:
            print(f"\nError: {str(e)}")

if __name__ == "__main__":
    chat()
