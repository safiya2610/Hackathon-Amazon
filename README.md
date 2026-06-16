# Amazon Recommerce 🌱
<img width="1500" height="800" alt="image" src="https://github.com/user-attachments/assets/4d301e10-5420-4eb8-8298-2820f788e3a0" />

An innovative e-commerce platform built for the **Amazon Hackathon**. Amazon Recommerce bridges the gap between traditional retail, sustainable second-hand shopping, and local community marketplaces. 

Built with **Django**, this project aims to reduce carbon footprints by encouraging users to buy used items, resell locally, and donate intelligently with the power of AI.

##  Key Features

* **Three-Tier Marketplace:** Buy and sell **New** products, **Used** items, and **Local** goods (with $0 delivery fees for neighbor-to-neighbor trades).
* **AI-Powered Sustainability:** Integrates with the **Google Gemini API** (`gemini-1.5-flash`). When sellers upload an image of a used item, the AI analyzes it to detect if it's old clothing, books, or a heavily worn item, and gently prompts the seller to **donate it** instead of selling.
* **Green Points System:** Buyers are rewarded with "Green Points" for choosing to buy used items instead of new ones, gamifying the sustainability experience.
* **Modern UI/UX:** Features a sleek, responsive design mimicking premium e-commerce interfaces, including pure-CSS promotional banners, horizontal scrolling product carousels, and high-quality product cards.
* **Fully Featured Cart & Checkout:** Includes user authentication, shopping carts, billing addresses, and order processing.

---

##  Technology Stack
* **Backend:** Python, Django
* **Database:** SQLite (Default for development)
* **Frontend:** HTML5, CSS3, Vanilla JavaScript, Bootstrap
* **AI Integration:** Google Gemini API (Generative AI)

---

##  How to Run the Project Locally

Follow these instructions to get your local development environment up and running.

### 1. Clone the repository
```bash
git clone https://github.com/safiya2610/Hackathon-Amazon.git
cd Hackathon-Amazon
```

### 2. Set up a Virtual Environment
It is highly recommended to use a virtual environment to manage dependencies.
**For Windows:**
```bash
pip install virtualenv
virtualenv env
env\Scripts\activate
```
**For Mac/Linux:**
```bash
pip install virtualenv
virtualenv env
source env/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Note: If you face version conflicts, ensure you are using the specific versions outlined in your requirements file, such as Django==2.2.4).*

### 4. Set your Environment Variables
You will need a Gemini API Key for the AI features to work.
* Create a `.env` file in the root directory (where `manage.py` is).
* Add your API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 5. Run Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create a Superuser (Admin Account)
```bash
python manage.py createsuperuser
```
Follow the prompts to set your admin username, email, and password.

### 7. Start the Development Server
```bash
python manage.py runserver
```

### 8. Access the Application
Open your web browser and navigate to:
* **Main Website:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* **Admin Dashboard:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) (Log in with the superuser account you created)

---


