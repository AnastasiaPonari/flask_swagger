# app.py
from flask import Flask, request, jsonify
from flasgger import Swagger, swag_from
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medical_services.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///medical_services.db')


# инициализация SQLAlchemy
db = SQLAlchemy(app)

migrate = Migrate(app, db)
# for db migrations
# flask db init    # First time only
# flask db migrate -m "Description of changes"
# flask db upgrade

# инициализация Swagger
swagger = Swagger(app)

# Модель данных для врачебных услуг
class MedicalService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String(100), nullable=False)
    doctor_specialty = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    is_available = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'service_name': self.service_name,
            'doctor_specialty': self.doctor_specialty,
            'price': self.price,
            'is_available': self.is_available
        }

# Создание таблицы в базе данных
with app.app_context():
    db.create_all()

# Получение всех услуг с возможностью сортировки
@app.route('/api/services', methods=['GET'])
@swag_from({
    'tags': ['Врачебные услуги'],
    'summary': 'Получите все медицинские услуги с возможностью сортировки',
    'parameters': [
        {
            'name': 'sort_by',
            'in': 'query',
            'type': 'string',
            'description': 'Поле для сортировки (id, service_name, doctor_specialty, price)',
            'required': False
        },
    ],
    'responses': {
        200: {
            'description': 'Список врачебных услуг',
            'schema': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer'},
                        'service_name': {'type': 'string'},
                        'doctor_specialty': {'type': 'string'},
                        'price': {'type': 'number'},
                        'is_available': {'type': 'boolean'}
                    }
                }
            }
        }
    }
})
def get_services():
    sort_by = request.args.get('sort_by', 'id')
    # order = request.args.get('order', 'asc')
    
    # Проверка допустимости поля для сортировки
    if not hasattr(MedicalService, sort_by):
        return jsonify({'error': f'Неизвестное поле для сортировки: {sort_by}'}), 400
    
    # Применение сортировки
    sort_field = getattr(MedicalService, sort_by)
    # if order.lower() == 'desc':
    sort_field = sort_field.asc()
    
    services = MedicalService.query.order_by(sort_field).all()
    return jsonify([service.to_dict() for service in services])

# Получение статистики по числовым полям
@app.route('/api/services/stats', methods=['GET'])
@swag_from({
    'tags': ['Врачебные услуги'],
    'summary': 'Получите статистику по числовым полям',
    'parameters': [
        {
            'name': 'field',
            'in': 'query',
            'type': 'string',
            'description': 'Числовое поле ( price )',
            'required': True
        }
    ],
    'responses': {
        200: {
            'description': 'Статистика по числовым полям',
            'schema': {
                'type': 'object',
                'properties': {
                    'field': {'type': 'string'},
                    'min': {'type': 'number'},
                    'max': {'type': 'number'},
                    'avg': {'type': 'number'}
                }
            }
        }
    }
})
def get_stats():
    field = request.args.get('field')
    
    # Проверка допустимости поля
    if field not in [ 'price', ]:
        return jsonify({'error': f'Неизвестное поле: {field}. Должно быть числовое.'}), 400
    
    field_column = getattr(MedicalService, field)
    
    # Получение статистики
    stats = db.session.query(
        func.min(field_column).label('min'),
        func.max(field_column).label('max'),
        func.avg(field_column).label('avg')
    ).first()
    
    return jsonify({
        'field': field,
        'min': stats.min,
        'max': stats.max,
        'avg': round(stats.avg, 2) if stats.avg else None
    })

# Добавление новой услуги
@app.route('/api/services', methods=['POST'])
@swag_from({
    'tags': ['Врачебные услуги'],
    'summary': 'Добавьте новую врачебную услугу',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'schema': {
                'type': 'object',
                'properties': {
                    'service_name': {'type': 'string'},
                    'doctor_specialty': {'type': 'string'},
                    'price': {'type': 'number'},
                    'is_available': {'type': 'boolean'}
                },
                'required': ['service_name', 'doctor_specialty', 'price',]
            }
        }
    ],
    'responses': {
        201: {
            'description': 'Услуга успешно добавлена',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'service': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'service_name': {'type': 'string'},
                            'doctor_specialty': {'type': 'string'},
                            'price': {'type': 'number'},
                            'is_available': {'type': 'boolean'}
                        }
                    }
                }
            }
        }
    }
})
def add_service():
    data = request.json
    required_fields = ['service_name', 'doctor_specialty', 'price',]

    # Проверка наличия всех необходимых полей
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Отсутствует обязательное поле: {field}'}), 400
        
            # Валидация данных
    if not isinstance(data['service_name'], str) or not data['service_name'].strip():
        return jsonify({'error': 'Название услуги должно быть непустой строкой'}), 400
            
    if not isinstance(data['doctor_specialty'], str) or not data['doctor_specialty'].strip():
        return jsonify({'error': 'Специальность врача должна быть непустой строкой'}), 400
            
        # Проверка, что цена - это число и оно положительное
    if not isinstance(data['price'], (int, float)) or data['price'] < 0:
        return jsonify({'error': 'Цена должна быть положительным числом'}), 400
            
    if 'is_available' in data and not isinstance(data['is_available'], bool):
        return jsonify({'error': 'Поле доступности должно быть логическим значением'}), 400
        
    
    # Создание новой услуги
    new_service = MedicalService(
        service_name=data['service_name'],
        doctor_specialty=data['doctor_specialty'],
        price=data['price'],
        is_available=data.get('is_available', True)
    )
    
    db.session.add(new_service)
    db.session.commit()
    
    return jsonify({
        'message': 'Услуга успешно добавлена',
        'service': new_service.to_dict()
    }), 201

# Получение услуги по ID
@app.route('/api/services/<int:service_id>', methods=['GET'])
@swag_from({
    'tags': ['Врачебные услуги'],
    'summary': 'Получите врачебную услугу по ID',
    'parameters': [
        {
            'name': 'service_id',
            'in': 'path',
            'type': 'integer',
            'required': True
        }
    ],
    'responses': {
        200: {
            'description': 'Врачебная услуга подробности',
            'schema': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'service_name': {'type': 'string'},
                    'doctor_specialty': {'type': 'string'},
                    'price': {'type': 'number'},
                    'is_available': {'type': 'boolean'}
                }
            }
        }
    }
})
def get_service(service_id):
    service = MedicalService.query.get(service_id)
    if not service:
        return jsonify({'error': 'Услуга не найдена'}), 404
    
    return jsonify(service.to_dict())

# Обновление услуги по ID
@app.route('/api/services/<int:service_id>', methods=['PUT'])
@swag_from({
    'tags': ['Врачебные услуги'],
    'summary': 'Обновите врачебную услугу по ID',
    'parameters': [
        {
            'name': 'service_id',
            'in': 'path',
            'type': 'integer',
            'required': True
        },
        {
            'name': 'body',
            'in': 'body',
            'schema': {
                'type': 'object',
                'properties': {
                    'service_name': {'type': 'string'},
                    'doctor_specialty': {'type': 'string'},
                    'price': {'type': 'number'},
                    'is_available': {'type': 'boolean'}
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Услуга успешно обновлена',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'service': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'service_name': {'type': 'string'},
                            'doctor_specialty': {'type': 'string'},
                            'price': {'type': 'number'},
                            'is_available': {'type': 'boolean'}
                        }
                    }
                }
            }
        },
        400: {
            'description': 'Неверный формат запроса',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        }
    }
})
def update_service(service_id):
    service = MedicalService.query.get(service_id)
    if not service:
        return jsonify({'error': 'Услуга не найдена'}), 404
    
    data = request.json
    
    # Обновление полей услуги
    if 'service_name' in data:
        service.service_name = data['service_name']
    if 'doctor_specialty' in data:
        service.doctor_specialty = data['doctor_specialty']
    if 'price' in data:
        service.price = data['price']
    if 'is_available' in data:
        service.is_available = data['is_available']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Услуга успешно обновлена',
        'service': service.to_dict()
    })

# Удаление услуги по ID
@app.route('/api/services/<int:service_id>', methods=['DELETE'])
@swag_from({
    'tags': ['Врачебные услуги'],
    'summary': 'Удалите врачебную услугу по ID',
    'parameters': [
        {
            'name': 'service_id',
            'in': 'path',
            'type': 'integer',
            'required': True
        }
    ],
    'responses': {
        200: {
            'description': 'Услуга успешно удалена',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def delete_service(service_id):
    service = MedicalService.query.get(service_id)
    if not service:
        return jsonify({'error': 'Услуга не найдена'}), 404
    
    db.session.delete(service)
    db.session.commit()
    
    return jsonify({'message': f'Услуга {service_id} успешно удалена'})

# Добавление тестовых данных для примера
@app.route('/api/populate', methods=['POST'])
@swag_from({
    'tags': ['Utility'],
    'summary': 'Добавьте тестовые данные для примера',
    'responses': {
        200: {
            'description': 'Database populated successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'count': {'type': 'integer'}
                }
            }
        }
    }
})
def populate_data():
    with app.app_context():
        db.drop_all()
        db.create_all()
    # Пример данных
    sample_services = [
        {
            'service_name': 'Консультация терапевта',
            'doctor_specialty': 'Терапевт',
            'price': 1500.0,
            'is_available': True
        },
        {
            'service_name': 'Консультация кардиолога',
            'doctor_specialty': 'Кардиолог',
            'price': 2500.0,
            'is_available': True
        },
        {
            'service_name': 'УЗИ брюшной полости',
            'doctor_specialty': 'Диагностика',
            'price': 3000.0,
            'is_available': True
        },
        {
            'service_name': 'Анализ крови общий',
            'doctor_specialty': 'Лаборатория',
            'price': 800.0,
            'is_available': True
        },
        {
            'service_name': 'Массаж спины',
            'doctor_specialty': 'Физиотерапия',
            'price': 2000.0,
            'is_available': True
        },
        {
            'service_name': 'МРТ головного мозга',
            'doctor_specialty': 'Диагностика',
            'price': 8000.0,
            'is_available': True
        },
        {
            'service_name': 'Прием невролога',
            'doctor_specialty': 'Невролог',
            'price': 2800.0,
            'is_available': True
        }
    ]
    
    # Очистка существующих данных
    db.session.query(MedicalService).delete()
    
    # Добавление новых данных
    for service_data in sample_services:
        service = MedicalService(**service_data)
        db.session.add(service)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Sample data added successfully',
        'count': len(sample_services)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True)