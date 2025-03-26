# Analytics AI - Database Chat Assistant

Analytics AI is an intelligent chat interface for querying databases using natural language. It uses AI to translate your questions into SQL queries, execute them on your database, and return results with visualizations where appropriate.

## Architecture Overview

The application consists of two main components:

1. **Frontend**: A React-based web application built with TypeScript and TailwindCSS
2. **Backend**: A Python-based FastAPI service with LLM integration for database querying

```
┌─────────────────┐        WebSocket/HTTP         ┌─────────────────────────┐
│                 │◄─────────────────────────────►│                         │
│                 │                               │                         │
│  React Frontend │                               │  FastAPI Backend        │
│                 │                               │  - Query Translation    │
│  - Chat UI      │                               │  - Database Connection  │
│  - Visualization│                               │  - Result Processing    │
│  - DB Selection │                               │  - Visualization        │
│                 │                               │                         │
└─────────────────┘                               └─────────────┬───────────┘
                                                               │
                                                               │ SQL Queries
                                                               ▼
                                                  ┌─────────────────────────┐
                                                  │                         │
                                                  │  PostgreSQL Database    │
                                                  │                         │
                                                  └─────────────────────────┘
```

## Prerequisites

- Node.js (v18+)
- Python (v3.9+)
- PostgreSQL
- OpenAI API key

## Installation

### Backend Setup

1. Navigate to the API directory:
   ```bash
   cd api
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Create a `.env` file in the api directory with the following variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_HOST=localhost
   POSTGRES_PORT=54320
   MODEL_NAME=gpt-4o
   ```
   Adjust the PostgreSQL connection details according to your setup.

6. Start the backend server:
   ```bash
   python api.py
   ```
   The API will be available at http://localhost:8001

### Frontend Setup

1. Navigate to the root directory of the project

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```
   The frontend will be available at http://localhost:5173

## Configuration

### Database Configuration

The application is designed to work with PostgreSQL databases. Make sure your PostgreSQL server is running and accessible.

If you need to adjust database connection parameters, modify the `.env` file in the api directory.

### Model Configuration

By default, the application uses the GPT-4o model from OpenAI. You can change this by modifying the `MODEL_NAME` variable in the `.env` file.

## Usage

1. Open the application in your browser (http://localhost:5173)
2. From the sidebar, select a database and schema
3. Once connected, you can start asking questions about your data
4. The AI will translate your questions into SQL, query the database, and return results
5. When appropriate, the results will include visualizations

### Example Queries

- "List all departments"
- "How many employees are in each department?"
- "Show me the salary distribution by department"
- "Who are the top 5 highest-paid employees?"

## Features

- **Natural Language Queries**: Ask questions about your data in plain language
- **Real-time Interaction**: WebSocket-based communication for responsive chat
- **Automatic Visualization**: Data is automatically visualized when appropriate
- **Multiple Database Support**: Switch between different databases and schemas
- **Persistent Chat History**: Chat sessions are saved and can be resumed
- **Error Handling**: Clear error messages for troubleshooting

## Troubleshooting

### Connection Issues

- Ensure your PostgreSQL server is running
- Verify database credentials in the `.env` file
- Check network settings if connecting to a remote database

### API Key Issues

- Make sure your OpenAI API key is valid and has sufficient credits
- Check that the key is correctly specified in the `.env` file

### Visualization Errors

- The visualization directory (`./visualizations`) should be writable by the API process
- Ensure matplotlib and seaborn are properly installed

## Development

### Building for Production

To create a production build of the frontend:

```bash
npm run build
```

The built files will be in the `dist` directory.

### API Development

The backend uses FastAPI, which includes automatic API documentation.
Access the API docs at http://localhost:8001/docs when the server is running.

## License

[MIT](LICENSE)