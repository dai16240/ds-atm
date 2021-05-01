# Import modules
from flask import (
	Flask,
	jsonify,
	request,
	make_response,
	render_template
)
import dataset
import uuid
from werkzeug.security import (
	generate_password_hash,
	check_password_hash
)
import jwt
import datetime
import os
from functools import wraps

# create Flask app instance
app = Flask(__name__)
# get secret key from environmet (heroku)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
# get database uri from environment (heroku)
database_uri = os.environ.get('DATABASE_URL')

# connect to database
db = dataset.connect(database_uri)


def token_required(f):
	@wraps(f)
	def decorated(*args, **kwargs):
		data = request.get_json()

		try:
			token = data['token']
		except:
			token = None

		if not token:
			return jsonify({'message': 'Token is missing!'}), 401
		try:
			data = jwt.decode(token, app.config['SECRET_KEY'])
			current_user = db['users'].find_one(public_id=data['public_id'])
		except:
			return jsonify('Token is invalid!'), 401
		return f(current_user, *args, **kwargs)
	return decorated


@app.route('/withdraw', methods=['PUT'])
@token_required
def withdraw(current_user):
	data = request.get_json()
	try:
		amount = data['amount']
	except:
		amount = None

	if not amount:
		return jsonify({'message': 'Missing parameters!'}), 400

	current_user['balance'] -= amount

	db['users'].update(current_user, ['public_id'])
	
	return jsonify({'message': f'-{amount}'})


@app.route('/deposit', methods=['PUT'])
@token_required
def deposit(current_user):
	data = request.get_json()
	try:
		amount = data['amount']
	except:
		amount = None

	if not amount:
		return jsonify({'message': 'Missing parameters!'}), 400

	current_user['balance'] += amount

	db['users'].update(current_user, ['public_id'])
	
	return jsonify({'message': f'+{amount}'})


@app.route('/balance', methods=['GET'])
@token_required
def balance(current_user):
	return jsonify({'name': current_user['name'], 'balance': current_user['balance']})


@app.route('/register', methods=['POST'])
def register():
	data = request.get_json()
	print(data)

	hashed_password = generate_password_hash(data['password'], method='sha256')
	new_user = {
		'public_id': str(uuid.uuid4()),
		'name': data['name'],
		'password': hashed_password,
		'balance': 0
	}
	db['users'].insert(new_user)

	return jsonify({'message': 'New user created!'})


@app.route('/login', methods=['POST'])
def login():
	data = request.get_json()

	try:
		u_name = data['name']
		u_pass = data['password']
	except:
		u_name = None
		u_pass = None

	if not u_name or not u_pass:
		return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login Required!"'})

	u = db['users'].find_one(name=u_name)
	if not u:
		return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login Required!"'})

	if check_password_hash(u['password'], u_pass):
		token = jwt.encode({'public_id': u['public_id'], 'exp': datetime.datetime.utcnow()+datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'])

		return jsonify({'token': token.decode('UTF-8')}) 

	return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login Required!"'})


@app.route('/')
def index():
	return render_template('index.html')
