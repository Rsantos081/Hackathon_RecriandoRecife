from app import create_app
import os

app = create_app()
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

if __name__ == '__main__':
    app.run(debug=True)