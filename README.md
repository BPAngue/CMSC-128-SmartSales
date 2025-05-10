
# SmartSales: Daily Sales Tracking and Forecasting System

A Django-based sales management system designed for small businesses to record, manage, and analyze daily sales transactions with ARIMA-based forecasting.

---

## 📦 Project Setup Guide

### 1️⃣ **Clone the Repository**
```bash
git clone <your-repository-link>
cd CMSC-128-SmartSales
```

---

### 2️⃣ **Set Up a Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # For Linux/Mac
venv\Scripts\activate     # For Windows
```

---

### 3️⃣ **Install Required Dependencies**
```bash
pip install -r requirements.txt
```
> If `requirements.txt` is missing, install manually:
```bash
pip install django pandas numpy pmdarima scikit-learn matplotlib
```

---

### 4️⃣ **Apply Migrations and Load Data**
```bash
python manage.py makemigrations
python manage.py migrate
```

#### (Optional) Load Mock Data:
```bash
python manage.py loaddata mock_data.json
```

---

### 5️⃣ **Run the Development Server**
```bash
python manage.py runserver
```

Access the system at [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## 📅 **Sales Forecasting Notes**
- Ensure mock data covers **daily**, **weekly**, and **monthly** sales periods for accurate ARIMA predictions.
- Forecasting is triggered automatically when accessing the dashboard.

---

## 📚 **Project Structure**
```
CMSC-128-SmartSales/
├── smartsales/
│   ├── manage.py
│   ├── smartsales/
│   └── smartsalesapp/
├── mock_data.json  # (Place your mock data file here)
└── README.md
```
