# Tourist Money Manager

A cross-platform mobile app for managing tourist finances, built with BeeWare/Toga. Track expenses, manage your budget, and get smart financial advice from an AI assistant.

![image](https://github.com/user-attachments/assets/a6c21f11-6091-42c3-8c6f-82f2931eab28)

"Tourist Money Manager" is a financial application designed specifically for travelers. This app allows users to log every transaction in various currencies, which are automatically converted to the user's home currency. With an informative dashboard, users can easily monitor total spending, remaining budget, and a breakdown of expenses by category.

The standout feature of this app is the **Tour-Fin AI Assistant**, powered by Google Gemini. This assistant can provide spending analysis, saving tips, and local recommendations based on the user's financial data in *real-time*. The app uses a local SQLite database for *offline-first* functionality, ensuring that data can be accessed and recorded even without an internet connection.

## Key Features

- **Financial Dashboard:** Visualize your financial summary, including total budget, total spending, today's expenses, and remaining budget.
- **Multi-Currency Transaction Logging:** Log expenses in various foreign currencies. The app will automatically convert them to your home currency using real-time exchange rates.
- **Tour-Fin AI Assistant:** Get personalized financial advice, spending pattern analysis, and travel tips from an AI assistant that is integrated with your financial data.
- **Budget Management:** Set a travel budget and track your remaining funds in *real-time* to keep your spending in check.
- **Reports & History:** View detailed expense breakdowns by category (e.g., Food, Transportation) and a history of your recent transactions.
- **Offline-First with Local Database:** All transaction data is stored locally on your device, allowing you to use the app without an internet connection.
- **Real-time Exchange Rates:** Syncs the latest currency exchange rates from [ExchangeRate-API](https://www.exchangerate-api.com/) when the app is connected to the internet.

## Tech Stack

- **Python 3.8+**
- **BeeWare / Toga:** For building the cross-platform user interface (UI).
- **Pony ORM:** For interacting with the local SQLite database.
- **Requests:** For making calls to external APIs (Exchange Rate & Gemini).
- **Briefcase:** For packaging the app for desktop and mobile platforms.

## Prerequisites

- Python 3.8 or later
- Git
- (Optional) Xcode for iOS builds
- (Optional) Java & Android SDK for Android builds

## Project Structure

```
tourist-money-manager/
├── src/
│   └── chatbotcrud/
│       ├── __init__.py
│       └── app.py         # Main application logic, UI, and database
├── requirements.txt
├── briefcase.toml
└── ...
```

## Installation

1.  **Clone this repository**
    ```bash
    git clone https://github.com/username/tourist-money-manager.git
    cd tourist-money-manager
    ```

2.  **Create and activate a virtual environment**
    ```bash
    python -m venv venv
    # Windows (PowerShell):
    .\venv\Scripts\Activate.ps1
    # macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install dependencies**
    ```bash
    pip install --upgrade pip setuptools
    pip install -r requirements.txt
    pip install briefcase
    ```

    *Required contents of `requirements.txt`:*
    ```txt
    toga
    pony
    requests
    httpx
    ```

## Configuration

Before running the application, you **must** configure the API Keys.

1.  **Get API Keys:**
    -   **ExchangeRate-API:** Get a free API key from [exchangerate-api.com](https://www.exchangerate-api.com/).
    -   **Google Gemini:** Get a free API key from [Google AI Studio (formerly MakerSuite)](https://makersuite.google.com/app/apikey).

2.  **Enter the API Keys:**
    Open the `src/chatbotcrud/app.py` file and replace the placeholder values in the following lines:

    ```python
    # Replace with your API Key
    EXCHANGE_RATE_API_KEY = "YOUR_EXCHANGERATE_API_KEY"
    EXCHANGE_RATE_API_URL = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_RATE_API_KEY}/latest/IDR"

    # Replace with your API Key
    GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
    ```

## Development

Run the app on your desktop for quick UI and logic testing:
```bash
briefcase dev
```
- The application window will appear, showing the main dashboard.
- Test the "Add Transaction," "AI Assistant," and "Settings" flows.
- Check the console or logs for errors.

## Packaging & Deployment

**Desktop (macOS, Windows, Linux)**
```bash
briefcase create
briefcase build
briefcase run
```

**Android**
```bash
briefcase create android
briefcase build android
briefcase run android
```

**iOS**
```bash
briefcase create iOS
briefcase build iOS
# Open the generated Xcode project to sign & run on a simulator/device
```

**Web**
```bash
briefcase create web
briefcase build web
briefcase run web
```
