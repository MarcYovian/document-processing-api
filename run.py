from src.document_api import create_app, settings

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=settings.APP_DEBUG)