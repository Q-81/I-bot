from api import db
from datetime import datetime, timedelta, time
import matplotlib.pyplot as plt


class TgUser(db.Model):
    tg_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    nickname = db.Column(db.String(100), nullable=True)
    created_on = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    def __repr__(self):
        return f"Nickname: {self.nickname}. TelegramId: {self.tg_id}"


def does_tg_user_exist(user_id):
    return TgUser.query.filter_by(tg_id=user_id).first() is not None


class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('tg_user.tg_id'), nullable=False)
    owner = db.relationship('TgUser', backref=db.backref('sessions', lazy=True))
    started_at = db.Column(db.DateTime, nullable=False)
    finished_at = db.Column(db.DateTime, nullable=True)


def is_session_finished(user_id):
    return Session.query.filter_by(owner=TgUser.query.get(user_id), finished_at=None).first() is None


def switch_session_status(user_id):
    user = TgUser.query.get(user_id)
    last_session = Session.query.filter_by(owner=user, finished_at=None).first()
    if last_session:
        last_session.finished_at = datetime.now()
        db.session.commit()
        return "finished"
    else:
        new_session = Session(owner=user, started_at=datetime.now())
        db.session.add(new_session)
        db.session.commit()
        return "created"


def get_and_restart_sessions():
    unfinished_sessions = Session.query.filter(Session.finished_at == None).all()

    for old_session in unfinished_sessions:
        old_session.finished_at = old_session.started_at.replace(hour=23, minute=59, second=59)
        new_date = old_session.started_at.date() + timedelta(days=1)
        new_time = time(0, 0, 1)

        new_session = Session(owner=old_session.owner, started_at=datetime.combine(new_date, new_time))
        db.session.add(new_session)
        db.session.commit()

    return f'Successfully transferred {len(unfinished_sessions)} session(s)!', len(unfinished_sessions)


def compute_activity_stats(user_id: str, n: int = 14):
    n_days_ago = datetime.now() - timedelta(days=n)

    recent_sessions = Session.query.filter(Session.started_at >= n_days_ago).all()

    sum_per_days = {}
    for session in recent_sessions:
        if session.finished_at is None:
            continue
        else:
            delta = session.finished_at - session.started_at
            key = session.started_at.date()
            value = sum_per_days.get(key, timedelta())
            sum_per_days[key] = value + delta

    x = [key.strftime('%d.%m') for key in sum_per_days.keys()]
    y = [value.seconds / 60**2 for key, value in sum_per_days.items()]
    avg = sum(y) / len(y)
    plt.figure(figsize=(8, 6))
    plt.title(f"График активности за последние {n} дней")
    plt.plot(x, y, marker='.', markersize=20, label=f'Среднее: {avg:.2f} ч / д')
    plt.xticks(rotation=90)
    plt.legend()
    path = f'instance/reports/{user_id}.png'
    plt.savefig(path)
    plt.clf()
    return 'Success!', path


class ParsedReminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('tg_user.tg_id', name='fk_tg_user_id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    remind_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    sent = db.Column(db.Boolean, nullable=True, default=False)

    def __repr__(self):
        return f'<ParsedReminder {self.id}>'


def add_reminder(user_id: int, reminder: str, entities: dict = None):
    """
    Adds one reminder to the DataBase.
    :param user_id: tg_user id, int
    :param reminder: main text to be sent, str
    :param entities: dictionary of classified entities of the reminder, like idx: {'word': '', 'ent_type': ''}, dict
    :return: 'Success' / 'Error'
    """

    new_reminder = ParsedReminder(
        user_id=user_id,
        text=reminder
    )
    db.session.add(new_reminder)
    db.session.commit()
    response = 'Success! Reminder was added.'

    # --- Add some details about the reminder --- #
    if entities:
        for i, entity in entities.items():
            if entity['ent_type'] == 'ORG':
                org_id = add_organization(entity['word'])
                intersection = ReminderORGIntersection(reminder_id=new_reminder.id, organization_id=org_id)
                db.session.add(intersection)
                db.session.commit()
        response = 'Success! Reminder with tags was added.'

    return response


def add_date_to_reminder(_date: str):
    reminder = ParsedReminder.query.order_by(ParsedReminder.created_at.desc()).first()
    reminder.remind_at = datetime.strptime(_date + ' 09:00:00', "%d.%m.%Y %H:%M:%S")
    db.session.commit()
    return f'Success! Date was added to the reminder with id {reminder.id}'


def add_time_to_reminder(_time: str):
    reminder = ParsedReminder.query.order_by(ParsedReminder.created_at.desc()).first()
    reminder.remind_at = reminder.remind_at.replace(
        hour=int(_time.split(':')[0]),
        minute=int(_time.split(':')[1])
    )
    db.session.commit()
    return f'Success! Time was added to the reminder with id {reminder.id}'


def check_for_reminders(delta=1):
    current_time = datetime.now()
    # Query for ParsedReminder records within the time range
    close_reminders = ParsedReminder.query.filter(
        ParsedReminder.remind_at >= current_time - timedelta(minutes=delta),
        ParsedReminder.remind_at <= current_time + timedelta(minutes=delta),
        ParsedReminder.sent == False
    ).all()

    # --- Collect founded reminders --- #
    reminders = {}
    for idx, reminder in enumerate(close_reminders):
        reminders[idx] = {
            'user_id': reminder.user_id,
            'text': reminder.text,
            'remind_at': reminder.remind_at
        }
        reminder.sent = True
        db.session.commit()

    return reminders


class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    def __repr__(self):
        return f'<Organization {self.name}>'


class ReminderORGIntersection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reminder_id = db.Column(db.Integer, db.ForeignKey('parsed_reminder.id', name='fk_parsed_reminder_id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id', name='fk_organization_id'))

    # Define back references
    reminder_relation = db.relationship('ParsedReminder', backref='reminder_org')
    company_relation = db.relationship('Organization', backref='reminder_org')


def compute_org_stats(user_id: str, n: int = 14):
    n_days_ago = datetime.now() - timedelta(days=n)
    recent_reminders = (
        ParsedReminder.query
        .filter(ParsedReminder.created_at >= n_days_ago)
        .filter(ParsedReminder.user_id == user_id)
        .all()
    )
    # print(recent_reminders)
    organization_counts = {}

    for reminder in recent_reminders:
        print(reminder)
        linked_organizations = (
            Organization.query
            .join(ReminderORGIntersection, ReminderORGIntersection.organization_id == Organization.id)
            .filter(ReminderORGIntersection.reminder_id == reminder.id)
            .all()
        )
        print(linked_organizations)

        for organization in linked_organizations:
            organization_counts[organization.name] = organization_counts.get(organization.name, 0) + 1

    # Print the organization counts
    for organization, count in organization_counts.items():
        print(f"{organization}: {count}")

    plt.figure(figsize=(8, 6))
    plt.title(f"Наиболее часто упоминаемые организации за последние {n} дней")
    plt.pie(organization_counts.values(), labels=organization_counts.keys())
    # plt.xticks(rotation=90)
    # plt.legend()
    path = f'instance/reports/{user_id}.png'
    plt.savefig(path)
    plt.clf()
    return 'Success!', path


# class Person(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False, unique=True)
#
#     def __repr__(self):
#         return f'<Person {self.name}>'
#
#
# class Location(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False, unique=True)
#
#     def __repr__(self):
#         return f'<Location {self.name}>'



def add_organization(org_name):
    existing_organization = Organization.query.filter_by(name=org_name).first()
    if existing_organization:
        # Organization with the given name already exists
        return existing_organization.id  # Return the ID of the existing organization
    else:
        # Create a new organization
        new_organization = Organization(name=org_name)
        db.session.add(new_organization)
        db.session.commit()
        return new_organization.id  # Return the ID of the newly created organization



