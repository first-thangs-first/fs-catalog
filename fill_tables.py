from models import Base, User, Category, CatalogItem

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine

import string
import random

engine = create_engine('sqlite:///catalog.db')

Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

records = {
    'Soccer': ['Cleats', 'Soccer Ball', 'Shorts', 'Tops', 'Net', 'Goalie Glove'],
    'Baseball': ['Bat', 'Mitt', 'Baseballs', 'Mound'],
    'Football': ['Helmet', 'Cleats', 'Football', 'Shoulder Pads'],
    'Basketball': ['Basketball', 'Practice Jerseys', 'Hoop', 'Socks'],
    'Hockey': ['Hockey Stick', 'Mitt', 'Helmet', 'Puck']
}


def make_gibberish(num_of_words):
    result = []
    for i in xrange(num_of_words + 1):
        w = [random.choice(string.ascii_lowercase) for x in xrange(random.randint(1, 10))]  # noqa
        word = ''.join(w)
        result.append(word)
    return result[0].capitalize() + string.join(result[1:], " ") + "end."

for category in records.keys():
    categoryRecord = Category(name=category)
    session.add(categoryRecord)
    session.commit()
    categoryRecord = session.query(Category).filter_by(name=category).one()
    for item in records[category]:
        description = make_gibberish(20)
        catalogItemRecord = CatalogItem(name=item,
                                        description=description,
                                        category_id=categoryRecord.id)
        session.add(catalogItemRecord)
    session.commit()

# insert cataglogItems
