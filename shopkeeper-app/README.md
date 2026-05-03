# Shopkeeper Pro - Comprehensive Shop Management Suite

Shopkeeper Pro is a multi-platform application designed to help shopkeepers manage their inventory, track sales, and analyze business performance. This suite includes a Python-based inventory backend, a Java-based sales analytics backend, a professional React web dashboard, and a React Native mobile application.

## Project Structure

- `backend-python/`: FastAPI application for Inventory Management (Products, Stock).
- `backend-java/`: Spring Boot application for Sales Tracking.
- `frontend-web/`: React + Vite dashboard for shopkeepers.
- `mobile-app/`: React Native application for mobile access.
  - **Release APK**: Located at `mobile-app/android/app/build/outputs/apk/release/app-release.apk`.

## Features

- **Inventory Management**: Add, update, delete, and view products with real-time stock tracking.
- **Professional Dashboard**: Clean and modern web interface using Tailwind CSS.
- **Mobile Access**: View inventory on the go with the Android application.
- **Dual Backend**: Leveraging the best of Python (FastAPI) for agility and Java (Spring Boot) for robust transaction tracking.

## Getting Started

### Python Backend
```bash
cd backend-python
pip install -r requirements.txt
uvicorn main:app --reload
```

### Java Backend
```bash
cd backend-java
./gradlew bootRun
```

### Web Frontend
```bash
cd frontend-web
npm install
npm run dev
```

### Mobile App
The pre-built release APK is available in the `mobile-app` directory. To run in development:
```bash
cd mobile-app
npm install
npx react-native run-android
```

## Professional Standards
- Clean, modular code following language-specific best practices.
- Comprehensive API documentation.
- Modern UI/UX with Tailwind CSS and Lucide Icons.
- Production-ready APK generation.
