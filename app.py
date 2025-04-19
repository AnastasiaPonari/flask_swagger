# app.py
from flask import Flask, request, jsonify
from flasgger import Swagger, swag_from
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medical_services.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize Swagger
swagger = Swagger(app)

# Модель данных для врачебных услуг   напиши сама создпдим 
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
    'tags': ['Medical Services'],
    'summary': 'Get all medical services with optional sorting',
    'parameters': [
        {
            'name': 'sort_by',
            'in': 'query',
            'type': 'string',
            'description': 'Field to sort by (id, service_name, doctor_specialty, price)',
            'required': False
        },
        # {
        #     'name': 'order',
        #     'in': 'query',
        #     'type': 'string',
        #     'description': 'Sort order (asc, desc)',
        #     'required': False
        # }
    ],
    'responses': {
        200: {
            'description': 'List of medical services',
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
        return jsonify({'error': f'Invalid sort field: {sort_by}'}), 400
    
    # Применение сортировки
    sort_field = getattr(MedicalService, sort_by)
    # if order.lower() == 'desc':
    sort_field = sort_field.desc()
    
    services = MedicalService.query.order_by(sort_field).all()
    return jsonify([service.to_dict() for service in services])

# Получение статистики по числовым полям
@app.route('/api/services/stats', methods=['GET'])
@swag_from({
    'tags': ['Medical Services'],
    'summary': 'Get statistics for numerical fields',
    'parameters': [
        {
            'name': 'field',
            'in': 'query',
            'type': 'string',
            'description': 'Numerical field ( price )',
            'required': True
        }
    ],
    'responses': {
        200: {
            'description': 'Statistics for the specified field',
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
        return jsonify({'error': f'Invalid field for statistics: {field}. Must be a numerical field.'}), 400
    
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
    'tags': ['Medical Services'],
    'summary': 'Add a new medical service',
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
            'description': 'Service created successfully',
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
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
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
        'message': 'Service added successfully',
        'service': new_service.to_dict()
    }), 201

# Получение услуги по ID
@app.route('/api/services/<int:service_id>', methods=['GET'])
@swag_from({
    'tags': ['Medical Services'],
    'summary': 'Get a medical service by ID',
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
            'description': 'Medical service details',
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
        return jsonify({'error': 'Service not found'}), 404
    
    return jsonify(service.to_dict())

# Обновление услуги по ID
@app.route('/api/services/<int:service_id>', methods=['PUT'])
@swag_from({
    'tags': ['Medical Services'],
    'summary': 'Update a medical service by ID',
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
            'description': 'Service updated successfully',
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
def update_service(service_id):
    service = MedicalService.query.get(service_id)
    if not service:
        return jsonify({'error': 'Service not found'}), 404
    
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
        'message': 'Service updated successfully',
        'service': service.to_dict()
    })

# Удаление услуги по ID
@app.route('/api/services/<int:service_id>', methods=['DELETE'])
@swag_from({
    'tags': ['Medical Services'],
    'summary': 'Delete a medical service by ID',
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
            'description': 'Service deleted successfully',
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
        return jsonify({'error': 'Service not found'}), 404
    
    db.session.delete(service)
    db.session.commit()
    
    return jsonify({'message': f'Service with ID {service_id} deleted successfully'})

# Добавление тестовых данных для примера
@app.route('/api/populate', methods=['POST'])
@swag_from({
    'tags': ['Utility'],
    'summary': 'Populate database with sample data',
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