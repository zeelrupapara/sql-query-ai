# Natural Language to SQL Chatbot

A conversational AI system that converts natural language questions into SQL queries and provides data visualizations.

## Features

- 🤖 Natural language to SQL conversion
- 📊 Interactive data visualizations
- 🔐 User authentication system
- 💾 Query caching for better performance
- 📈 Automatic chart type selection
- 🔄 Follow-up question suggestions
- 📋 Database schema inspection

## Installation

1. Clone the repository: (Optional)
```bash
git clone https://github.com/yourusername/nl2sql-chatbot.git
cd nl2sql-chatbot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install requirements:
```bash
pip install -r requirements.txt
```

4. Create a .env file with your OpenAI API key:
```bash
OPENAI_API_KEY=your_api_key_here
```

## Usage

1. Start the application:
```bash
python app.py
```

2. Open your browser and navigate to the displayed URL (typically http://localhost:8501)

3. Register/Login to access the system

4. Upload your SQLite database file

5. Start asking questions about your data

## System Architecture

### Core Components:

1. **Query Processing Pipeline**
   - Natural language understanding
   - Query classification
   - SQL generation
   - Result visualization

2. **Authentication System**
   - User registration
   - Login/logout functionality
   - Session management

3. **Data Management**
   - SQLite database handling
   - Schema extraction
   - Query caching

### Key Functions:

- `process_query()`: Main pipeline for handling user questions
- `classify_query()`: Determines if question can be answered with available data
- `generate_sql()`: Converts natural language to SQL
- `create_visualization()`: Generates appropriate charts for results

## Example Questions (Any Question Can be asked related to Database or Non-DB related)

- "Show me sales trends over the last 6 months"
- "Which products have the highest profit margin?"
- "Compare performance across different regions"
- "What are the top 10 customers by revenue?"

## Requirements

- Python 3.8+
- OpenAI API key
- SQLite database
- Required packages listed in requirements.txt

## Project Structure

```
nl2sql-chatbot/
├── streamlit_app.py    # Main application
├── nl2sql.py          # Query processing logic
├── auth.py            # Authentication system
├── database.py        # Database operations
├── visualization.py   # Chart generation
├── utils.py          # Helper functions
├── cache.py          # Caching system
├── follow_up.py      # Follow-up suggestions
├── requirements.txt   # Dependencies
└── README.md         # Documentation
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for GPT-4 API
- Streamlit for the web framework
- SQLite for database management

## Support

For support, please open an issue in the GitHub repository or contact the maintenance team.