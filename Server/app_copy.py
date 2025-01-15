from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_cors import CORS
from bson.objectid import ObjectId
from bson.json_util import dumps
from werkzeug.security import generate_password_hash, check_password_hash
import requests

# Flask 앱 초기화
app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/smart_glasses_db"  # MongoDB URI
mongo = PyMongo(app)
CORS(app)

# 네이버 API 키
NAVER_CLIENT_ID = ""
NAVER_CLIENT_SECRET = ""

# 컬렉션 참조
users = mongo.db.users
routes = mongo.db.routes
stores = mongo.db.store

# 기본 라우트
@app.route('/')
def home():
    return jsonify({"message": "Flask 서버가 실행 중입니다!"})


### 사용자 관리 ###
# 사용자 등록
@app.route('/register', methods=['POST'])
def register_user():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({"error": "모든 필드를 입력하세요"}), 400

    if users.find_one({"email": email}):
        return jsonify({"error": "이미 존재하는 이메일입니다"}), 400

    hashed_password = generate_password_hash(password)
    users.insert_one({"name": name, "email": email, "password": hashed_password})
    return jsonify({"message": "사용자 등록 완료"}), 201


# 사용자 로그인
@app.route('/login', methods=['POST'])
def login_user():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user = users.find_one({"email": email})
    if not user or not check_password_hash(user['password'], password):
        return jsonify({"error": "이메일 또는 비밀번호가 잘못되었습니다"}), 401

    return jsonify({"message": "로그인 성공", "user_id": str(user['_id'])}), 200


### 경로 검색 ###
@app.route('/route/search', methods=['GET'])
def search_route():
    start_x = request.args.get('start_x')
    start_y = request.args.get('start_y')
    end_x = request.args.get('end_x')
    end_y = request.args.get('end_y')

    if not (start_x and start_y and end_x and end_y):
        return jsonify({"error": "모든 좌표 정보를 입력하세요"}), 400

    # 네이버 경로 API 요청
    url = "https://naveropenapi.apigw.ntruss.com/map-direction/v1/driving"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
    }
    params = {
        "start": f"{start_x},{start_y}",
        "goal": f"{end_x},{end_y}",
        "option": "trafast"  # 최적 경로
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        return jsonify(response.json()), 200
    else:
        return jsonify({
            "error": "경로 검색 실패",
            "details": response.text
        }), response.status_code


# 주소 -> 좌표 변환
@app.route('/geocode/address', methods=['GET'])
def address_to_coordinates():
    address = request.args.get('address')

    if not address:
        return jsonify({"error": "주소를 입력하세요"}), 400

    url = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
    }
    params = {"query": address}

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        return jsonify(response.json()), 200
    else:
        return jsonify({"error": "주소 변환 실패", "details": response.text}), response.status_code


# 좌표 -> 주소 변환
@app.route('/geocode/coordinates', methods=['GET'])
def coordinates_to_address():
    latitude = request.args.get('latitude')
    longitude = request.args.get('longitude')

    if not (latitude and longitude):
        return jsonify({"error": "위도와 경도를 입력하세요"}), 400

    url = "https://naveropenapi.apigw.ntruss.com/map-reversegeocode/v2/gc"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
    }
    params = {
        "coords": f"{longitude},{latitude}",
        "orders": "addr",  # 주소만 반환
        "output": "json"
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        return jsonify(response.json()), 200
    else:
        return jsonify({"error": "좌표 변환 실패", "details": response.text}), response.status_code


# 경로 저장
@app.route('/route/save', methods=['POST'])
def save_route():
    data = request.json
    user_id = data.get('user_id')
    route_data = data.get('route_data')

    if not user_id or not route_data:
        return jsonify({"error": "사용자 ID와 경로 데이터를 입력하세요"}), 400

    route_id = routes.insert_one({
        "user_id": user_id,
        "route_data": route_data
    }).inserted_id

    return jsonify({"message": "경로 저장 완료", "route_id": str(route_id)}), 201


# 특정 사용자 경로 조회
@app.route('/routes/<user_id>', methods=['GET'])
def get_routes(user_id):
    user_routes = routes.find({"user_id": user_id})
    return dumps(user_routes), 200


### 상점 관리 ###
# 상점 추가
@app.route('/store', methods=['POST'])
def add_store():
    data = request.json
    name = data.get('name')
    location = data.get('location')
    products = data.get('products')
    hours = data.get('hours')

    if not name or not location or not products or not hours:
        return jsonify({"error": "모든 필드를 입력하세요"}), 400

    store_id = stores.insert_one({
        "name": name,
        "location": location,
        "products": products,
        "hours": hours
    }).inserted_id

    return jsonify({"message": "상점 추가 완료", "store_id": str(store_id)}), 201


# 특정 지역의 상점 조회 (위도/경도 기반)
@app.route('/stores/location', methods=['GET'])
def get_stores_by_location():
    latitude = float(request.args.get('latitude'))
    longitude = float(request.args.get('longitude'))
    radius = float(request.args.get('radius', 5))  # 기본 반경 5km

    # MongoDB 지리적 검색
    stores_nearby = stores.find({
        "location": {
            "$geoWithin": {
                "$centerSphere": [[longitude, latitude], radius / 6378.1]  # 반경을 km로 계산
            }
        }
    })
    return dumps(stores_nearby), 200


# 특정 상점 상세 조회
@app.route('/store/<store_id>', methods=['GET'])
def get_store(store_id):
    store = stores.find_one({"_id": ObjectId(store_id)})
    if not store:
        return jsonify({"error": "상점을 찾을 수 없습니다"}), 404
    return dumps(store), 200


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
