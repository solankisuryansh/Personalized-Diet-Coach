from flask import Flask, request, jsonify, render_template
import os
from datetime import datetime
import json
import google.generativeai as genai

app = Flask(__name__)

# Load your API key for Gemini
gemini_api_key = "YOUR_GEMINI_API_KEY"
genai.configure(api_key=gemini_api_key)

conversation_history = {}
user_data = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data['message']
        session_id = data.get('session_id', 'default')
        
        # Initialize session if it doesn't exist
        if session_id not in conversation_history:
            conversation_history[session_id] = []
            user_data[session_id] = {
                "collection_stage": "age",
                "age": None,
                "weight": None,
                "height": None,
                "diet_preference": None,
                "goal": None,
                "complete": False
            }
        
        # Process user message based on collection stage
        stage = user_data[session_id]["collection_stage"]
        
        # Add user message to conversation for display
        conversation_history[session_id].append({
            "role": "user", 
            "content": user_message
        })
        
        # Process message based on current stage
        if stage == "age":
            try:
                age = int(user_message.strip())
                user_data[session_id]["age"] = age
                user_data[session_id]["collection_stage"] = "weight"
                reply = f"Thanks! I've recorded your age as {age} years. Now, please tell me your weight in kg."
            except ValueError:
                reply = "Please enter your age as a number (e.g., 25)."
                
        elif stage == "weight":
            try:
                weight = float(user_message.strip())
                user_data[session_id]["weight"] = weight
                user_data[session_id]["collection_stage"] = "height"
                reply = f"Got it! Your weight is {weight} kg. Next, please share your height in cm."
            except ValueError:
                reply = "Please enter your weight as a number in kg (e.g., 70)."
                
        elif stage == "height":
            try:
                height = float(user_message.strip())
                user_data[session_id]["height"] = height
                user_data[session_id]["collection_stage"] = "diet_preference"
                reply = f"Thanks! I've recorded your height as {height} cm. What are your dietary preferences? (e.g., vegetarian, vegan, non-vegetarian, pescatarian, etc.)"
            except ValueError:
                reply = "Please enter your height as a number in cm (e.g., 175)."
                
        elif stage == "diet_preference":
            user_data[session_id]["diet_preference"] = user_message
            user_data[session_id]["collection_stage"] = "goal"
            reply = "Great! Now, please tell me your fitness goal (e.g., weight loss, muscle gain, maintenance, improved health, etc.)."
            
        elif stage == "goal":
            user_data[session_id]["goal"] = user_message
            user_data[session_id]["collection_stage"] = "complete"
            user_data[session_id]["complete"] = True
            
            # Generate personalized diet plan using Gemini
            user_info = user_data[session_id]
            
            try:
                # Configure the model - using Gemini Pro for text generation
                model = genai.GenerativeModel('gemini-pro')
                
                # Create the prompt - Gemini doesn't use system prompts the same way as OpenAI
                prompt = f"""You are a professional dietician. Create a personalized diet plan based on the user's information. 
                Include a daily meal plan with specific foods and portions. Format your response with clear sections for 
                Breakfast, Lunch, Dinner, and Snacks. Include calorie estimates and nutrition tips.

                Please create a detailed diet plan for me with the following information:
                - Age: {user_info['age']}
                - Weight: {user_info['weight']} kg
                - Height: {user_info['height']} cm
                - Dietary preference: {user_info['diet_preference']}
                - Fitness goal: {user_info['goal']}"""
                
                # Generate the response - simpler approach using just the prompt
                response = model.generate_content(prompt)
                
                reply = response.text
            except Exception as e:
                print(f"Gemini API error: {str(e)}")
                # Fallback plan in case of API issues
                reply = generate_fallback_diet_plan(user_info)
            
        else:
            # If user wants another diet plan after completion
            if "new plan" in user_message.lower() or "reset" in user_message.lower():
                user_data[session_id]["collection_stage"] = "age"
                user_data[session_id]["complete"] = False
                reply = "Let's create a new diet plan! Please tell me your age."
            else:
                # Send any other queries to the AI
                try:
                    model = genai.GenerativeModel('gemini-pro')
                    
                    prompt = f"""You are a professional dietician. Answer the user's nutrition and diet-related questions based on their profile.
                    
                    User profile:
                    - Age: {user_data[session_id]['age']}
                    - Weight: {user_data[session_id]['weight']} kg
                    - Height: {user_data[session_id]['height']} cm
                    - Dietary preference: {user_data[session_id]['diet_preference']}
                    - Fitness goal: {user_data[session_id]['goal']}
                    
                    User question: {user_message}"""
                    
                    response = model.generate_content(prompt)
                    
                    reply = response.text
                except Exception as e:
                    print(f"Gemini API error: {str(e)}")
                    reply = "I'm having trouble generating a response right now. Could you try asking a different question?"
        
        # Add assistant reply to conversation history
        conversation_history[session_id].append({
            "role": "assistant", 
            "content": reply
        })
        
        # Keep conversation history manageable
        if len(conversation_history[session_id]) > 20:
            conversation_history[session_id] = conversation_history[session_id][-20:]
        
        return jsonify({
            'reply': reply,
            'session_id': session_id,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'collection_stage': user_data[session_id]["collection_stage"]
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            'reply': "I'm having trouble processing that. Could you please try again?",
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'error': str(e)
        }), 200  # Return 200 instead of 500 to handle in the frontend

def generate_fallback_diet_plan(user_info):
    """Generate a basic diet plan when the API fails"""
    
    goal = user_info['goal'].lower()
    diet_pref = user_info['diet_preference'].lower()
    
    # Calculate BMI
    height_m = user_info['height'] / 100
    bmi = user_info['weight'] / (height_m * height_m)
    
    # Base calories
    if "weight loss" in goal:
        daily_calories = 1800 if bmi > 25 else 2000
    elif "muscle gain" in goal:
        daily_calories = 2500 if bmi < 25 else 2300
    else:  # maintenance
        daily_calories = 2200 if bmi > 25 else 2400
    
    # Adjust for diet preferences
    if "vegan" in diet_pref or "vegetarian" in diet_pref:
        protein_sources = "tofu, tempeh, legumes, beans, and plant-based protein powder"
    else:
        protein_sources = "chicken breast, fish, eggs, lean beef, and protein powder"
    
    return f"""
# Personalized Diet Plan

Based on your profile:
- Age: {user_info['age']}
- Weight: {user_info['weight']} kg
- Height: {user_info['height']} cm
- Dietary preference: {user_info['diet_preference']}
- Fitness goal: {user_info['goal']}

I've created the following diet plan for you.

## Daily Calorie Target: {daily_calories} calories

## Meal Plan

### Breakfast (25% of daily calories):
- Protein source (eggs or {protein_sources if "vegan" not in diet_pref else "protein smoothie with plant protein"})
- Complex carbs (oatmeal or whole grain toast)
- Healthy fat (avocado or nuts)
- Fruit (berries or banana)

### Lunch (30% of daily calories):
- Lean protein ({protein_sources})
- Complex carbs (brown rice or quinoa)
- Vegetables (mixed salad with leafy greens)
- Healthy fat (olive oil dressing)

### Dinner (25% of daily calories):
- Lean protein ({protein_sources})
- Vegetables (steamed or roasted non-starchy vegetables)
- Small portion of complex carbs
- Healthy fat (olive oil or nuts)

### Snacks (20% of daily calories):
- Mid-morning: Greek yogurt with berries or plant-based equivalent
- Mid-afternoon: Apple with a small handful of nuts
- Evening (optional): Protein shake or vegetable sticks with hummus

## Nutrition Tips for {user_info['goal']}:

1. Stay hydrated by drinking at least 2-3 liters of water daily
2. Limit processed foods and added sugars
3. Aim for at least 5 servings of vegetables and fruits daily
4. {"Create a calorie deficit through portion control and regular exercise" if "weight loss" in goal else "Ensure adequate protein intake to support muscle recovery and growth" if "muscle" in goal else "Maintain a balanced diet with regular meal timing"}
5. Consider tracking your food intake for the first few weeks to stay on target

Feel free to adjust portions based on your hunger levels and activity. This plan can be modified as you progress toward your goals.
"""

@app.route('/reset', methods=['POST'])
def reset_conversation():
    session_id = request.json.get('session_id', 'default')
    if session_id in conversation_history:
        conversation_history[session_id] = []
        user_data[session_id] = {
            "collection_stage": "age",
            "age": None,
            "weight": None,
            "height": None,
            "diet_preference": None,
            "goal": None,
            "complete": False
        }
    
    return jsonify({'status': 'success', 'message': 'Conversation reset successfully'})

@app.route('/nutrition', methods=['GET'])
def get_nutrition_tips():
    category = request.args.get('category', 'general')
    
    tips = {
        'general': [
            "Aim for at least 5 servings of fruits and vegetables daily",
            "Stay hydrated by drinking at least 8 glasses of water per day",
            "Limit processed foods and added sugars",
            "Include protein with every meal to feel fuller longer"
        ],
        'weightloss': [
            "Create a calorie deficit by consuming fewer calories than you burn",
            "Focus on nutrient-dense foods that keep you satisfied",
            "Include regular physical activity alongside dietary changes",
            "Eat slowly and mindfully to recognize fullness cues"
        ],
        'muscle': [
            "Consume 1.6-2.2g of protein per kg of bodyweight daily",
            "Include complex carbohydrates to fuel workouts",
            "Timing nutrition around workouts can optimize results",
            "Stay hydrated for optimal performance and recovery"
        ]
    }
    
    return jsonify({
        'category': category,
        'tips': tips.get(category, tips['general'])
    })

if __name__ == '__main__':
    app.run(debug=True)