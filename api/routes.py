from api import app, db, clf, morph

from api import models

from flask import request, jsonify, make_response


@app.route('/api/check_user/<int:tg_id>', methods=['GET'])
def check_user(tg_id):
    user_exists = models.does_tg_user_exist(tg_id)
    return jsonify({'user_exists': user_exists})


@app.route('/api/add_user', methods=['POST'])
def add_user():
    tg_user = request.json
    new_user = models.TgUser(tg_id=tg_user['id'],
                             first_name=tg_user['first_name'],
                             last_name=tg_user['last_name'])
    db.session.add(new_user)
    db.session.commit()
    response = make_response(jsonify({'user_added': True}))
    response.status_code = 200

    return response


@app.route('/api/parse_reminder', methods=['POST'])
def parse_reminder():
    text = request.json['text']
    tokens = clf(text)

    words = []  # list of tuples, is allowed to contain empty tuples

    # --- Current word & Type of entity --- #
    word, ent_type = '', None

    for entity in tokens:
        if 'B-' in entity['entity']:
            words.append((word, ent_type))  # saving collected word
            word = text[entity['start']:entity['end']]  # new word collection starting
            ent_type = entity['entity'].split('-')[1]  # ORG, LOC, PER
        else:
            word += text[entity['start']:entity['end']]  # add to current word

    words.append((word, ent_type))

    # --- RESPONSE COLLECTION --- #
    out = {}
    for idx, (word, ent_type) in enumerate(words):
        if word != '' and ent_type:  # check if tuple is meaningful
            parsed_word = morph.parse(word)[0]
            out[idx] = {
                'word': parsed_word.normal_form,
                # parsed_word.inflect({'nomn', 'sing'}).word, <- inflect can return None
                'ent_type': ent_type
            }

    return jsonify(out), 302 if len(out) != 0 else 404


@app.route('/api/add_reminder', methods=['POST'])
def add_reminder():
    payload = request.json
    if payload.get('tags', None):
        response = models.add_reminder(
            user_id=payload['user']['id'],
            reminder=payload['text'],
            entities=payload['tags']
        )
    else:
        response = models.add_reminder(
            user_id=payload['user']['id'],
            reminder=payload['text']
        )
    return jsonify({'result': response}), 201


@app.route('/api/update_reminder', methods=['POST'])
def update_reminder():
    payload = request.json
    if payload.get('date', None):
        response = models.add_date_to_reminder(_date=payload['date'])
    elif payload.get('time', None):
        response = models.add_time_to_reminder(_time=payload['time'])
    else:
        return jsonify({'result': 'Error during updating the reminder!'}), 400

    return jsonify({'result': response}), 200


@app.route('/api/check_for_updates', methods=['GET'])
def get_close_reminders():
    response = models.check_for_reminders(delta=1)
    status = 302 if len(response) != 0 else 404
    return jsonify(response), status


@app.route('/api/sessions', methods=['GET'])
def get_last_session():
    try:
        user_id = request.json.get('id', None)
        if user_id is None:
            return jsonify({"error": "No user id provided"}), 400

        if not models.does_tg_user_exist(user_id):
            return jsonify({"error": "User does not exist"}), 400

        is_session_finished = models.is_session_finished(user_id)

        return jsonify({"is_finished": is_session_finished}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/sessions', methods=['POST'])
def create_session():
    try:
        user_id = request.json.get('id')
        return jsonify({"result": models.switch_session_status(user_id)}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/check_for_sessions', methods=['GET'])
def transfer_sessions():
    response, k_sessions = models.get_and_restart_sessions()
    status = 201 if k_sessions > 0 else 304
    return jsonify({'result': response}), status


@app.route('/api/compute_stats', methods=['POST'])
def compute_session_stats():
    query = request.args
    response, path = models.compute_activity_stats(n=int(query['n']), user_id=query['user_id'])
    return jsonify({'result': response, 'path': path}), 200


@app.route('/api/compute_analysis', methods=['POST'])
def compute_entity_analysis():
    query = request.args
    if query['type'] == 'ORG':
        response, path = models.compute_org_stats(n=int(query['n']), user_id=query['user_id'])
        return jsonify({'result': response, 'path': path}), 200
    else:
        return jsonify({'result': 'Not supported yet'}), 400