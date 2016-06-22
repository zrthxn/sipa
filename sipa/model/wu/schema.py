# -*- coding: utf-8; -*-
from sqlalchemy import (Column, Index, Integer, String,
                        text, Text, ForeignKey, DECIMAL, BigInteger, Date)
from sqlalchemy.orm import relationship, column_property

from sipa.model.sqlalchemy import db

import logging
logger = logging.getLogger(__name__)


DORMITORY_MAPPINGS = [
    'Wundstraße 5',
    'Wundstraße 7',
    'Wundstraße 9',
    'Wundstraße 11',
    'Wundstraße 1',
    'Wundstraße 3',
    'Zellescher Weg 41',
    'Zellescher Weg 41A',
    'Zellescher Weg 41B',
    'Zellescher Weg 41C',
    'Zellescher Weg 41D',
    'Borsbergstraße 34',
    'Zeunerstraße 1f',
]


class Nutzer(db.Model):
    __tablename__ = 'nutzer'
    __table_args__ = (
        Index(u'zimmer', u'etage', u'zimmernr'),
    )

    nutzer_id = Column(Integer, primary_key=True, server_default=text("'0'"))
    wheim_id = Column(Integer, nullable=False, index=True,
                      server_default=text("'0'"))
    etage = Column(Integer, nullable=False, server_default=text("'0'"))
    zimmernr = Column(String(10), nullable=False, server_default=text("''"))
    unix_account = Column(String(40), nullable=False, unique=True)
    status = Column(Integer, nullable=False, index=True,
                    server_default=text("'1'"))

    computer = relationship("Computer", backref="nutzer")
    credit_entries = relationship('Credit', backref="nutzer")

    @property
    def address(self):
        try:
            return "{} / {} {}".format(
                DORMITORY_MAPPINGS[self.wheim_id - 1],
                self.etage,
                self.zimmernr,
            )
        except IndexError:
            logger.warning("No dormitory mapping given for `wheim_id`=%s",
                           self.wheim_id)
            return ""

    transactions = relationship(
        'Buchung',
        primaryjoin=("or_("
                     "Nutzer.nutzer_id==Buchung.haben_uid,"
                     "Nutzer.nutzer_id==Buchung.soll_uid"
                     ")"),
        foreign_keys="[Buchung.soll_uid, Buchung.haben_uid]",
        backref='nutzer',
    )


class Computer(db.Model):
    __tablename__ = 'computer'

    nutzer_id = Column(Integer, ForeignKey('nutzer.nutzer_id'), nullable=False)

    c_etheraddr = Column(String(20), primary_key=True)
    c_ip = Column(String(15), nullable=False, index=True, primary_key=True,
                  server_default=text("''"))
    c_hname = Column(String(20), nullable=False, server_default=text("''"))
    c_alias = Column(String(20))


class Credit(db.Model):
    __tablename__ = u'credit'

    user_id = Column(Integer, ForeignKey('nutzer.nutzer_id'),
                     primary_key=True, nullable=False)
    amount = Column(Integer, nullable=False)
    timetag = Column(Integer, primary_key=True, nullable=False)


class Traffic(db.Model):
    __tablename__ = 'tuext'
    __bind_key__ = 'traffic'

    timetag = Column(BigInteger(), primary_key=True)
    ip = Column(String(15), nullable=False, index=True, primary_key=True)
    input = Column(DECIMAL(20, 0))
    output = Column(DECIMAL(20, 0))
    overall = column_property(input + output)


class Buchung(db.Model):
    __tablename__ = 'buchungen'
    __bind_key__ = 'userman'

    oid = Column(Integer, nullable=False, primary_key=True)
    bkid = Column(Integer)
    fbid = Column(Integer)

    datum = Column(Date, nullable=False, default='')
    wert = Column(Integer, nullable=False, default=0)
    bes = Column(Text)

    soll_uid = Column(Integer)
    haben_uid = Column(Integer)

    def __repr__(self):
        return (
            "<{cls} {wert:.2f}€ Soll: {s_uid} → Haben: {h_uid} '{bes}'>"
            .format(
                cls=type(self).__name__,
                wert=self.wert/100,
                s_uid=self.soll_uid,
                h_uid=self.haben_uid,
                bes=self.bes,
            )
        )

    @property
    def effective_value(self):
        """Return the sign-corrected value in Euros.

        Switch the sign if `self.nutzer.uid` is the haben_uid, not the
        soll_uid.

        This uses the `nutzer` backref imposed by
        `Nutzer.transactions`, and raises a ValueError if the backref
        is invalid.
        """

        # Using the explicit (x=a and x!=b) form here to let the (x=a
        # and x=b) case lead to a ValueError
        if (self.soll_uid == self.nutzer.nutzer_id and
                self.haben_uid != self.nutzer.nutzer_id):
            return self.wert / 100
        elif self.haben_uid == self.nutzer.nutzer_id:
            return - self.wert / 100
        else:
            # this shouldn't happen, since `Buchung`en are only used
            # via the relationship in `Nutzer`.  The used join forbids
            # (uid != soll_uid AND uid != haben_uid).2
            raise ValueError("Uid of backref `nutzer` (%s) "
                             "is neither soll_uid (%s) nor haben_uid (%s)",
                             self.nutzer.nutzer_id, self.soll_uid, self.haben_uid)
