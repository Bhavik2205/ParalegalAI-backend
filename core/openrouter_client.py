from openai import OpenAI
import config

client = OpenAI(api_key=config.OPENROUTER_API_KEY, base_url=config.BASE_URL)

def generate_response(messages, model="openai/gpt-4o-mini", use_web=False, temperature=0.7, max_tokens=1000):
    """
    Generates a response from OpenRouter API using OpenAI SDK v1.x
    """

    try:
        if use_web:
            model = f"{model}:online"

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"Error in OpenRouter API call: {e}")
        return "Sorry, I encountered an issue processing your request."
