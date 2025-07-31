# Session Agent

A FastAPI-based session analysis agent with LLM integration.

## Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd session-agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   # Copy the example file
   cp env.example .env
   
   # Edit .env with your actual values
   # Add your OpenAI API key
   ```

4. **Run the server**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

5. **Test the API**
   - Visit: http://127.0.0.1:8000/docs
   - Try the `/analyze/{session_id}` endpoint

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required for LLM analysis)
- `MONGODB_URI`: MongoDB connection string (for future use)
- `MONGODB_DB`: MongoDB database name (for future use)

## Features

- Session analysis with real-time LLM integration
- Mock data support for testing
- FastAPI with automatic documentation
- Educational insights in Turkish 