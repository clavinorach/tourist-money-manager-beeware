import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, CENTER, LEFT
import os
from datetime import datetime, timedelta
from pony.orm import Database, Required, PrimaryKey, db_session, select, desc, sum
import requests
import json
import threading

# --- KELAS STYLE ---
class Styles:
    def __init__(self):
        self.colors = {
            'primary': '#3498db',
            'success': '#27ae60',
            'warning': '#f39c12',
            'danger': '#e74c3c',
            'dark': '#34495e',
            'light': '#ecf0f1',
            'white': '#ffffff',
            'text_primary': '#2c3e50'
        }
        self.main_container = Pack(direction=COLUMN, padding=20, background_color=self.colors['light'])
        self.header_title = Pack(font_size=24, padding_bottom=5, text_align=CENTER, color=self.colors['dark'])
        self.header_subtitle = Pack(font_size=14, padding_bottom=20, text_align=CENTER, color=self.colors['dark'])
        self.card_container = Pack(direction=ROW, padding_bottom=10)
        self.card = Pack(flex=1, direction=COLUMN, padding=15, background_color=self.colors['white'], alignment=CENTER)
        self.card_title = Pack(font_size=12, color=self.colors['dark'])
        self.card_value = Pack(font_size=18, font_weight='bold', color=self.colors['primary'])
        self.table = Pack(flex=1, padding_bottom=15)
        self.section_label = Pack(font_size=16, padding_top=20, padding_bottom=10, color=self.colors['dark'])
        self.form_box = Pack(direction=COLUMN, padding_bottom=10)
        self.form_row = Pack(direction=ROW, padding_bottom=10, alignment=CENTER)
        self.form_label = Pack(width=120, text_align=LEFT, padding_right=10)
        self.form_input = Pack(flex=1, padding=8, font_size=14)
        self.conversion_label = Pack(padding=15, text_align=CENTER, background_color=self.colors['white'], font_size=16, color=self.colors['dark'])
        self.button_box = Pack(direction=ROW, padding_top=20)
        self.button_primary = Pack(flex=1, padding=12, background_color=self.colors['success'], color=self.colors['white'])
        self.button_secondary = Pack(flex=1, padding=12, background_color=self.colors['warning'], color=self.colors['white'])
        self.button_danger = Pack(flex=1, padding=12, background_color=self.colors['danger'], color=self.colors['white'])
        self.button_dark = Pack(padding=10, background_color=self.colors['dark'], color=self.colors['white'])

# Konfigurasi Database
db = Database()

# Definisi Entity Database
class ConversionHistory(db.Entity):
    id = PrimaryKey(int, auto=True)
    from_currency = Required(str)
    to_currency = Required(str)
    amount = Required(float)
    result = Required(float)
    timestamp = Required(datetime, default=datetime.now)

class ExchangeRate(db.Entity):
    currency_code = PrimaryKey(str)
    rate = Required(float)
    last_updated = Required(datetime, default=datetime.now)

class Transaction(db.Entity):
    id = PrimaryKey(int, auto=True)
    description = Required(str)
    amount = Required(float)
    currency = Required(str)
    amount_home_currency = Required(float)
    category = Required(str)
    timestamp = Required(datetime, default=datetime.now)

class UserSettings(db.Entity):
    id = PrimaryKey(int, auto=True)
    home_currency = Required(str, default='IDR')
    travel_budget = Required(float, default=0.0)

# Konfigurasi API EXCHANGE RATE
EXCHANGE_RATE_API_KEY = ""  
EXCHANGE_RATE_API_URL = f"https://v6.exchangerate-api.com/v6/c32d1da56c35df5b3d4f08db/latest/IDR"

# API AI menggunakan Google Gemini 
GEMINI_API_KEY = "" 
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


# Konstanta Aplikasi
CURRENCY_MAP = {
    "US Dollar (USD)": "USD", "Japanese Yen (¥)": "JPY", "Euro (€)": "EUR",
    "British Pound (£)": "GBP", "Australian Dollar (A$)": "AUD", "Singapore Dollar (S$)": "SGD",
    "Malaysian Ringgit (RM)": "MYR", "Chinese Yuan (¥)": "CNY", "Indonesian Rupiah (IDR)": "IDR",
    "Thai Baht (THB)": "THB", "Korean Won (₩)": "KRW", "Philippine Peso (₱)": "PHP",
    "Vietnamese Dong (₫)": "VND"
}
REVERSE_CURRENCY_MAP = {code: name for name, code in CURRENCY_MAP.items()}
TRAVEL_CATEGORIES = [
    "Makanan & Minuman", "Transportasi", "Akomodasi", "Tiket Masuk",
    "Belanja", "Souvenir", "Kesehatan", "Komunikasi", "Lainnya"
]

class TouristMoneyManagerApp(toga.App):

    def startup(self):
        self.styles = Styles()
        self.setup_database()
        self.update_exchange_rates_from_api()
        self.chat_history = []
        self.main_window = toga.MainWindow(title=self.formal_name, size=(500, 700))
        self.main_window.content = self.build_dashboard()
        self.main_window.show()

    def setup_database(self):
        """Set up the database connection."""
        try:
            # Perbaikan path untuk Briefcase
            data_dir = self.paths.data
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)

            db_path = os.path.join(data_dir, 'tourist_money_manager.sqlite')
            db.bind(provider='sqlite', filename=db_path, create_db=True)
            db.generate_mapping(create_tables=True)

            with db_session:
                if not UserSettings.select().exists():
                    UserSettings(home_currency='IDR', travel_budget=0.0)

            return True
        except Exception as e:
            print(f"Database setup failed: {str(e)}")
            return False

    def get_user_settings(self):
        """Get user settings."""
        with db_session:
            settings = UserSettings.select().first()
            return settings if settings else UserSettings(home_currency='IDR', travel_budget=0.0)

    def update_exchange_rates_from_api(self):
        """Update exchange rates from API dengan API key."""
        try:
            if EXCHANGE_RATE_API_KEY == "YOUR_API_KEY_HERE":
                print("Warning: Exchange Rate API key not configured")
                return False
                
            response = requests.get(EXCHANGE_RATE_API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Cek status response dari exchangerate-api.com
            if data.get('result') == 'success' and 'conversion_rates' in data:
                rates = data['conversion_rates']
                with db_session:
                    for code in CURRENCY_MAP.values():
                        if code in rates and code != 'IDR':
                            rate = rates[code]
                            rate_obj = ExchangeRate.get(currency_code=code)
                            if rate_obj:
                                rate_obj.rate = rate
                                rate_obj.last_updated = datetime.now()
                            else:
                                ExchangeRate(currency_code=code, rate=rate)
                print("Exchange rates updated successfully")
                return True
            else:
                print(f"API Error: {data.get('error-type', 'Unknown error')}")
        except Exception as e:
            print(f"Failed to update exchange rates: {str(e)}")
        return False

    def get_exchange_rate(self, currency_code):
        """Get exchange rate from database."""
        if currency_code == 'IDR':
            return 1.0
        with db_session:
            rate_obj = ExchangeRate.get(currency_code=currency_code)
            return rate_obj.rate if rate_obj else None

    def convert_to_home_currency(self, amount, from_currency):
        """Convert amount to home currency."""
        settings = self.get_user_settings()
        home_currency = settings.home_currency
        if from_currency == home_currency:
            return amount
        if from_currency == 'IDR':
            rate = self.get_exchange_rate(home_currency)
            return amount * rate if rate else amount
        elif home_currency == 'IDR':
            rate = self.get_exchange_rate(from_currency)
            return amount / rate if rate else amount
        else:
            from_rate = self.get_exchange_rate(from_currency)
            to_rate = self.get_exchange_rate(home_currency)
            if from_rate and to_rate:
                idr_amount = amount / from_rate
                return idr_amount * to_rate
            return amount

    def build_dashboard(self):
        container = toga.Box(style=self.styles.main_container)
        title_label = toga.Label("Tourist Money Manager", style=self.styles.header_title)
        subtitle_label = toga.Label("Your Travel Finance Assistant", style=self.styles.header_subtitle)
        container.add(title_label)
        container.add(subtitle_label)
        summary = self.get_financial_summary()
        settings = self.get_user_settings()
        if settings.travel_budget > 0:
            budget_card = toga.Box(style=self.styles.card)
            budget_card.add(toga.Label("Travel Budget", style=self.styles.card_title))
            budget_card.add(toga.Label(f"{settings.travel_budget:,.0f} {settings.home_currency}", style=self.styles.card_value))
            remaining = settings.travel_budget - summary['total_spent']
            remaining_color = self.styles.colors['success'] if remaining >= 0 else self.styles.colors['danger']
            remaining_card = toga.Box(style=self.styles.card)
            remaining_card.add(toga.Label("Remaining Budget", style=self.styles.card_title))
            remaining_card.add(toga.Label(f"{remaining:,.0f} {settings.home_currency}", style=Pack(font_size=18, font_weight='bold', color=remaining_color)))
            card_row1 = toga.Box(style=self.styles.card_container)
            card_row1.add(budget_card)
            card_row1.add(remaining_card)
            container.add(card_row1)
        today_card = toga.Box(style=self.styles.card)
        today_card.add(toga.Label("Today's Spending", style=self.styles.card_title))
        today_card.add(toga.Label(f"{summary['today_spent']:,.0f} {settings.home_currency}", style=self.styles.card_value))
        total_card = toga.Box(style=self.styles.card)
        total_card.add(toga.Label("Total Trip Spending", style=self.styles.card_title))
        total_card.add(toga.Label(f"{summary['total_spent']:,.0f} {settings.home_currency}", style=self.styles.card_value))
        card_row2 = toga.Box(style=self.styles.card_container)
        card_row2.add(today_card)
        card_row2.add(total_card)
        container.add(card_row2)
        self.category_table = toga.Table(headings=['Category', 'Amount', 'Count'], style=self.styles.table)
        self.recent_table = toga.Table(headings=['Description', 'Amount', 'Category', 'Date'], style=self.styles.table)
        container.add(toga.Label("Spending by Category", style=self.styles.section_label))
        container.add(self.category_table)
        container.add(toga.Label("Recent Transactions", style=self.styles.section_label))
        container.add(self.recent_table)
        nav_box = toga.Box(style=self.styles.button_box)
        btn_add_transaction = toga.Button("Add Transaction", on_press=self.show_add_transaction, style=self.styles.button_primary)
        btn_ai_assistant = toga.Button("AI Assistant", on_press=self.show_ai_assistant, style=self.styles.button_secondary)
        nav_box.add(btn_add_transaction)
        nav_box.add(btn_ai_assistant)
        container.add(nav_box)
        btn_settings = toga.Button("Settings", on_press=self.show_settings, style=self.styles.button_dark)
        container.add(btn_settings)
        self.load_category_breakdown()
        self.load_recent_transactions()
        return container

    def build_add_transaction(self):
        container = toga.Box(style=self.styles.main_container)
        header_label = toga.Label("Add New Transaction", style=self.styles.header_title)
        container.add(header_label)
        form_box = toga.Box(style=self.styles.form_box)
        desc_label = toga.Label("Description", style=self.styles.form_label)
        self.transaction_description = toga.TextInput(placeholder="e.g., Lunch at Shibuya", style=self.styles.form_input)
        desc_row = toga.Box(style=self.styles.form_row)
        desc_row.add(desc_label)
        desc_row.add(self.transaction_description)
        form_box.add(desc_row)
        amount_label = toga.Label("Amount", style=self.styles.form_label)
        self.transaction_amount = toga.TextInput(placeholder="1500", on_change=self.on_amount_change, style=self.styles.form_input)
        amount_row = toga.Box(style=self.styles.form_row)
        amount_row.add(amount_label)
        amount_row.add(self.transaction_amount)
        form_box.add(amount_row)
        currency_label = toga.Label("Currency", style=self.styles.form_label)
        self.transaction_currency = toga.Selection(items=list(CURRENCY_MAP.keys()), on_select=self.on_currency_change, style=self.styles.form_input)
        currency_row = toga.Box(style=self.styles.form_row)
        currency_row.add(currency_label)
        currency_row.add(self.transaction_currency)
        form_box.add(currency_row)
        category_label = toga.Label("Category", style=self.styles.form_label)
        self.transaction_category = toga.Selection(items=TRAVEL_CATEGORIES, style=self.styles.form_input)
        category_row = toga.Box(style=self.styles.form_row)
        category_row.add(category_label)
        category_row.add(self.transaction_category)
        form_box.add(category_row)
        container.add(form_box)
        self.conversion_label = toga.Label("", style=self.styles.conversion_label)
        container.add(self.conversion_label)
        btn_box = toga.Box(style=self.styles.button_box)
        btn_save = toga.Button("Save Transaction", on_press=self.on_save_transaction, style=self.styles.button_primary)
        btn_back = toga.Button("Back to Dashboard", on_press=self.show_dashboard, style=self.styles.button_danger)
        btn_box.add(btn_save)
        btn_box.add(btn_back)
        container.add(btn_box)
        return container

    def build_ai_assistant(self):
        container = toga.Box(style=self.styles.main_container)
        header_label = toga.Label("Tour-Fin AI Assistant", style=self.styles.header_title)
        self.chat_display = toga.MultilineTextInput(readonly=True, style=Pack(flex=1, padding=10, font_size=12))
        input_box = toga.Box(style=Pack(direction=ROW, padding_top=10))
        self.chat_input = toga.TextInput(placeholder="Ask me about finance or local tips...", style=self.styles.form_input)
        btn_send = toga.Button("Send", on_press=self.on_send_message, style=self.styles.button_primary)
        btn_back = toga.Button("Back to Dashboard", on_press=self.show_dashboard, style=Pack(padding=10, background_color=self.styles.colors['danger'], color=self.styles.colors['white']))
        self.update_chat_display()
        input_box.add(self.chat_input)
        input_box.add(btn_send)
        container.add(header_label)
        container.add(self.chat_display)
        container.add(input_box)
        container.add(btn_back)
        return container

    def build_settings(self):
        container = toga.Box(style=self.styles.main_container)
        header_label = toga.Label("Settings", style=self.styles.header_title)
        container.add(header_label)
        settings = self.get_user_settings()
        form_box = toga.Box(style=self.styles.form_box)
        currency_label = toga.Label("Home Currency", style=self.styles.form_label)
        self.settings_home_currency = toga.Selection(
            items=list(CURRENCY_MAP.keys()),
            value=REVERSE_CURRENCY_MAP.get(settings.home_currency, "Indonesian Rupiah (IDR)"),
            style=self.styles.form_input
        )
        currency_row = toga.Box(style=self.styles.form_row)
        currency_row.add(currency_label)
        currency_row.add(self.settings_home_currency)
        form_box.add(currency_row)
        budget_label = toga.Label("Travel Budget", style=self.styles.form_label)
        self.settings_budget = toga.TextInput(
            value=str(settings.travel_budget),
            placeholder="Enter your travel budget",
            style=self.styles.form_input
        )
        budget_row = toga.Box(style=self.styles.form_row)
        budget_row.add(budget_label)
        budget_row.add(self.settings_budget)
        form_box.add(budget_row)
        container.add(form_box)
        btn_box = toga.Box(style=self.styles.button_box)
        btn_save = toga.Button("Save Settings", on_press=self.on_save_settings, style=self.styles.button_primary)
        btn_back = toga.Button("Back", on_press=self.show_dashboard, style=self.styles.button_danger)
        btn_box.add(btn_save)
        btn_box.add(btn_back)
        container.add(btn_box)
        return container

    def on_amount_change(self, widget):
        self.update_conversion_display()

    def on_currency_change(self, widget):
        self.update_conversion_display()

    def update_conversion_display(self):
        try:
            if not hasattr(self, 'transaction_amount') or not hasattr(self, 'transaction_currency'):
                return
            amount_str = self.transaction_amount.value
            currency_selection = self.transaction_currency.value
            if not amount_str or not currency_selection:
                self.conversion_label.text = ""
                return
            amount = float(amount_str.replace(",", "").replace(".", ""))
            currency_code = CURRENCY_MAP[currency_selection]
            settings = self.get_user_settings()
            converted = self.convert_to_home_currency(amount, currency_code)
            if currency_code != settings.home_currency:
                self.conversion_label.text = f"≈ {converted:,.0f} {settings.home_currency}"
            else:
                self.conversion_label.text = ""
        except (ValueError, KeyError):
            self.conversion_label.text = ""

    def on_save_transaction(self, widget):
        try:
            if not all([self.transaction_description.value, self.transaction_amount.value,
                        self.transaction_currency.value, self.transaction_category.value]):
                self.main_window.info_dialog("Validation Error", "All fields must be filled!")
                return
            amount = float(self.transaction_amount.value.replace(",", "").replace(".", ""))
            if amount <= 0:
                raise ValueError("Amount must be positive")
            currency_code = CURRENCY_MAP[self.transaction_currency.value]
            home_amount = self.convert_to_home_currency(amount, currency_code)
            with db_session:
                Transaction(
                    description=self.transaction_description.value, amount=amount,
                    currency=currency_code, amount_home_currency=home_amount,
                    category=self.transaction_category.value
                )
            self.main_window.info_dialog("Success", "Transaction saved successfully!")
            self.show_dashboard(widget)
        except ValueError as e:
            self.main_window.error_dialog("Invalid Input", str(e))
        except Exception as e:
            self.main_window.error_dialog("Error", f"Error saving transaction: {str(e)}")

    def on_save_settings(self, widget):
        try:
            home_currency = CURRENCY_MAP[self.settings_home_currency.value]
            budget = float(self.settings_budget.value.replace(",", "").replace(".", ""))
            with db_session:
                settings = UserSettings.select().first()
                if settings:
                    settings.home_currency = home_currency
                    settings.travel_budget = budget
                else:
                    UserSettings(home_currency=home_currency, travel_budget=budget)
            self.main_window.info_dialog("Success", "Settings saved successfully!")
            self.show_dashboard(widget)
        except ValueError:
            self.main_window.error_dialog("Invalid Input", "Invalid budget amount!")
        except Exception as e:
            self.main_window.error_dialog("Error", f"Error saving settings: {str(e)}")

    def on_send_message(self, widget):
        message = self.chat_input.value.strip()
        if not message:
            return
        self.chat_history.append({"role": "user", "content": message})
        self.chat_input.value = ""
        self.update_chat_display()
        self.chat_display.value += "\n\nAssistant: Thinking..."
        threading.Thread(target=self.fetch_ai_response).start()

    def fetch_ai_response(self):
        """Fetch AI response from Gemini in a separate thread."""
        response_text = self.get_ai_response_from_gemini(self.chat_history)
        
        # Tambahkan respons dari asisten ke riwayat chat
        self.chat_history.append({"role": "assistant", "content": response_text})

        # Jadwalkan pembaruan UI di main loop dari thread ini
        self.loop.call_soon_threadsafe(self.update_chat_display)

    def get_ai_response_from_gemini(self, conversation_history):
        """Mendapatkan respons AI dari Google Gemini API (gratis dan kompatibel dengan BeeWare)."""
        if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
            return "❌ Error: Gemini API Key belum dikonfigurasi. Silakan dapatkan API key gratis di https://makersuite.google.com/app/apikey"
        
        summary = self.get_financial_summary()
        settings = self.get_user_settings()
        
        # SYSTEM PROMPT YANG DIPERBAIKI DAN DIFORMAT DENGAN BAIK
        system_prompt = f"""🤖 **Tour-Fin AI Assistant** - Travel Finance Expert

Anda adalah asisten perjalanan yang ahli dalam:
• Manajemen Keuangan Perjalanan
• Rekomendasi Destinasi Wisata Indonesia
• Tips Budgeting dan Penghematan
• Saran Kuliner dan Budaya Lokal

📊 **DATA KEUANGAN USER SAAT INI:**
┌─────────────────────────────────────┐
│ Mata Uang Utama    : {settings.home_currency}           │
│ Total Pengeluaran  : {summary['total_spent']:,.0f} {settings.home_currency}    │
│ Pengeluaran Hari Ini: {summary['today_spent']:,.0f} {settings.home_currency}   │
│ Budget Perjalanan  : {settings.travel_budget:,.0f} {settings.home_currency}    │
│ Sisa Budget        : {(settings.travel_budget - summary['total_spent']):,.0f} {settings.home_currency} │
└─────────────────────────────────────┘

🎯 **INSTRUKSI RESPONS:**
✅ SELALU sebutkan data keuangan user dalam respons jika relevan
✅ Berikan analisis spending pattern berdasarkan data
✅ Saran penghematan atau peringatan jika budget menipis
✅ Respons dalam Bahasa Indonesia yang ramah dan informatif
✅ Berikan rekomendasi praktis dan actionable

📝 **CONTOH RESPONS YANG BAIK:**
"Berdasarkan data Anda, hari ini sudah menghabiskan {summary['today_spent']:,.0f} {settings.home_currency}. 
Total pengeluaran trip sudah mencapai {summary['total_spent']:,.0f} {settings.home_currency} dari budget {settings.travel_budget:,.0f} {settings.home_currency}..."

Selalu responsif, helpful, dan personal dalam setiap jawaban!"""

        # Format conversation untuk Gemini API
        conversation_text = f"{system_prompt}\n\n"
        for msg in conversation_history:
            role = "User" if msg['role'] == 'user' else "Assistant"
            conversation_text += f"{role}: {msg['content']}\n"
        
        # Ambil pertanyaan terakhir user
        last_user_message = ""
        for msg in reversed(conversation_history):
            if msg['role'] == 'user':
                last_user_message = msg['content']
                break
        
        # Payload untuk Gemini API
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"{system_prompt}\n\nUser: {last_user_message}\n\nBerikan respons yang informatif dan personal berdasarkan data keuangan user di atas."
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 500
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
        }
        
        try:
            # Request ke Gemini API
            url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'candidates' in data and len(data['candidates']) > 0:
                    candidate = data['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        ai_response = candidate['content']['parts'][0]['text'].strip()
                        return ai_response
                    else:
                        return "❌ Maaf, tidak ada respons yang diterima dari AI. Silakan coba lagi."
                else:
                    return "❌ Maaf, AI tidak dapat memberikan respons saat ini. Silakan coba dengan pertanyaan lain."
            else:
                error_data = response.json() if response.content else {}
                error_message = error_data.get('error', {}).get('message', 'Unknown error')
                print(f"Gemini API Error: {response.status_code} - {error_message}")
                return f"❌ Error API ({response.status_code}): {error_message}. Silakan periksa API key Anda."
                
        except requests.exceptions.Timeout:
            return "⏱️ Maaf, permintaan timeout. Silakan coba lagi."
        except requests.exceptions.ConnectionError:
            return "🔌 Maaf, tidak dapat terhubung ke server AI. Periksa koneksi internet Anda."
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}")
            return "❌ Terjadi kesalahan jaringan. Silakan coba lagi."
        except json.JSONDecodeError:
            return "❌ Error parsing response dari server. Silakan coba lagi."
        except Exception as e:
            print(f"Unexpected Error: {e}")
            return "❌ Terjadi kesalahan tak terduga. Silakan coba lagi."

    def update_chat_display(self):
        if hasattr(self, 'chat_display'):
            chat_text = []
            for msg in self.chat_history:
                role = "🧑 Anda" if msg['role'] == 'user' else "🤖 Assistant"
                chat_text.append(f"{role}: {msg['content']}")
            self.chat_display.value = "\n\n".join(chat_text)
            self.chat_display.scroll_to_bottom()

    def get_financial_summary(self):
        with db_session:
            today_start = datetime.combine(datetime.now().date(), datetime.min.time())
            total_spent = sum(t.amount_home_currency for t in Transaction.select()) or 0
            today_spent = sum(t.amount_home_currency for t in Transaction.select() if t.timestamp >= today_start) or 0
            return {'total_spent': total_spent, 'today_spent': today_spent}

    def load_category_breakdown(self):
        with db_session:
            categories = {}
            for t in Transaction.select():
                cat = t.category
                if cat not in categories:
                    categories[cat] = {'amount': 0, 'count': 0}
                categories[cat]['amount'] += t.amount_home_currency
                categories[cat]['count'] += 1
            settings = self.get_user_settings()
            table_data = [[cat, f"{data['amount']:,.0f} {settings.home_currency}", str(data['count'])]
                          for cat, data in sorted(categories.items(), key=lambda x: x[1]['amount'], reverse=True)]
            self.category_table.data = table_data

    def load_recent_transactions(self):
        with db_session:
            transactions = list(select(t for t in Transaction).order_by(desc(Transaction.timestamp))[:10])
            settings = self.get_user_settings()
            table_data = []
            for t in transactions:
                amount_str = (f"{t.amount:,.0f} {t.currency}" if t.currency == settings.home_currency else
                              f"{t.amount:,.2f} {t.currency} (≈{t.amount_home_currency:,.0f} {settings.home_currency})")
                table_data.append([t.description[:30] + ("..." if len(t.description) > 30 else ""),
                                   amount_str, t.category, t.timestamp.strftime("%m/%d %H:%M")])
            self.recent_table.data = table_data

    def show_dashboard(self, widget):
        self.main_window.content = self.build_dashboard()

    def show_add_transaction(self, widget):
        self.main_window.content = self.build_add_transaction()

    def show_ai_assistant(self, widget):
        self.main_window.content = self.build_ai_assistant()

    def show_settings(self, widget):
        self.main_window.content = self.build_settings()

def main():
    return TouristMoneyManagerApp(
        formal_name="Tourist Money Manager",
        app_id="com.example.touristmoneymanager",
        app_name="chatbotcrud"
    )