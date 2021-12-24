import os
import requests
import urllib.parse
import sqlite3

from flask import redirect, render_template, request, session
from functools import wraps

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") != "Elisadmin":
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

def eur(value):
    """Format value as USD."""
    return f"€{value:,.2f}"

# So useful, thanks Vishal from PyNative - https://pynative.com/python-sqlite-blob-insert-and-retrieve-digital-data/
def convertToBinaryData(filename):
    # Convert digital data to binary format
    with open(filename, 'rb') as file:
        blobData = file.read()
    return blobData

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_pending_orders():
    # Initialize the dict cursor
    db = sqlite3.connect("ptits_oignons.db", check_same_thread=False)
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    commandes_en_attente = cur.execute("""SELECT id, user_id, strftime("%d/%m/%Y", time) AS time, selling_point, total_price, status FROM commandes WHERE status = "En attente" ORDER BY time DESC""").fetchall()
    en_attente = []

    for commande in commandes_en_attente:
        name = cur.execute("""SELECT username FROM users WHERE id = ? """, (commande["user_id"],)).fetchone()
        commande = {
            "id" : commande["id"],
            "name" : name[0],
            "time" : commande["time"],
            "status" : commande["status"],
            "selling_point" : commande["selling_point"],
            "total_price" : commande["total_price"],
            "legumes" : []
        }
        commande_legumes = cur.execute("""SELECT legume_id, prix, qty FROM commandes_items WHERE commandes_id = ?""", [commande["id"]]).fetchall()
        for legume in commande_legumes:
            name_unit = cur.execute("""SELECT name, unit FROM legumes WHERE id = ?""", (legume["legume_id"],)).fetchone()
            legume = {"veg_name" : name_unit[0],
                "veg_unit" : name_unit[1],
                "veg_id" : legume["legume_id"],
                "veg_price" : legume["prix"],
                "veg_qty" : legume["qty"]}
            commande["legumes"].append(legume)
        en_attente.append(commande)

    # Kill cursor and connection to db
    cur.close()
    db.close()

    return en_attente

def get_pending_in_date_range(DateRange):
    # Initialize the dict cursor
    db = sqlite3.connect("ptits_oignons.db", check_same_thread=False)
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    commandes_en_attente = cur.execute("""SELECT id, user_id, strftime("%d/%m/%Y", time) AS time, selling_point, total_price FROM commandes WHERE status = "En attente" AND time BETWEEN ? AND ? ORDER BY time DESC""", DateRange).fetchall()
    en_attente = []

    for commande in commandes_en_attente:
        name = cur.execute("""SELECT username FROM users WHERE id = ? """, (commande["user_id"],)).fetchone()
        commande = {
            "id" : commande["id"],
            "name" : name[0],
            "time" : commande["time"],
            "selling_point" : commande["selling_point"],
            "total_price" : commande["total_price"],
            "legumes" : []
        }
        commande_legumes = cur.execute("""SELECT legume_id, prix, qty FROM commandes_items WHERE commandes_id = ?""", [commande["id"]]).fetchall()
        for legume in commande_legumes:
            name_unit = cur.execute("""SELECT name, unit FROM legumes WHERE id = ?""", (legume["legume_id"],)).fetchone()
            legume = {"veg_name" : name_unit[0],
                "veg_unit" : name_unit[1],
                "veg_id" : legume["legume_id"],
                "veg_price" : legume["prix"],
                "veg_qty" : legume["qty"]}
            commande["legumes"].append(legume)
        en_attente.append(commande)

    # Kill cursor and connection to db
    cur.close()
    db.close()

    return en_attente

def get_online_vegs():
    db = sqlite3.connect("ptits_oignons.db", check_same_thread=False)
    cur = db.cursor()

    online_vegs = cur.execute("""SELECT image, name, unit, prix_unit, status, id FROM legumes WHERE status = "online" """).fetchall()

    cur.close()
    db.close()

    return online_vegs

def get_offline_vegs():
    db = sqlite3.connect("ptits_oignons.db", check_same_thread=False)
    cur = db.cursor()

    # Loop the offline vegs (offline_legumes) pour dresser le tableau des légumes hors ligne
    offline_vegs = cur.execute("""SELECT name, unit, prix_unit, status, id FROM legumes WHERE status = "offline" """).fetchall()

    cur.close()
    db.close()

    return offline_vegs