# LES PETITS OIGNONS
#### Description:
The project is a webapp for my family business, which is basically vegetables and fruits farming.

It is basically an online store without the payment solution yet.
As the main user will be french, much of the names and id's are in french...
It enables people to take orders directly on the app where clients are able to log in, choose among available vegetables & fruits, then place the order to be delivered at a certain point.
Users receive an email in their inbox confirming the order is well taken and can consult the status of the order (if its read, shipped or deleted)
The project also features an admin access that enables the admin to do things such as put online and offline vegetables, change status of the orders, download an Excel recap of the orders, or add new vegetables to the proposed ones.

For the solutions implemented, I sticked to the Flask Python frame of development.
A database (ptits_oignons.db) contains users, vegetables, orders, and orders items:
- it is queried by users to sign in, order and follow their orders status;
- it is queried by the admin to add vegetabes, update values of the existing ones, manage orders, etc...

To keep the design part under control, I used Bootstrap version 4.5.3 and my own CSS.
The webapp should be fully responsive thanks to this design work.
Very slight touches of Javascript are included in the project, around Bootstrap items or to enrich forms.

##### Features and helpers
The additional features are:
- possibility to send mail (on order, to the client; on contact, to the admin),
- a pre-formatted Excel spreadsheet downloadable in one click by the admin to ease the logistics of orders preparation,
- an email validation check on client Register step, allowing to check if the adress exists to avoid fake registration,
- Google Maps API to locate delivery points

The app uses SQLite3 and Flask-Sessions to store inputs.
Querying the internet to have an idea of how to make a proper database structure for a shop, I realized that it wasn't mandatory to use database.
I also thought that my code was repeating enough in the querying, so I came up with the Flask-Sessions solution for the cart mainly.
Finding some tutorials helped me to better understand Python data structures and their manipulation: the cart is a list of dictionaries containing themselves a list of dictionaries.

###### Details of the folders and files
Les Petits Oignons, as a Flask app, has a standard organisation with:
- a **static** folder, where images and styles are stored, plus the uploaded images directory and the source download directory (Excel spreadsheets are stored there as a backup)
- **templates**, where HTML templates including Jinja2 snippets are stored. Templates ending with "_mail.html" are actually for the mails and not for standard displaying purposes.
- **app.py**, where the main code is written. It contains the sensitive data, such as API key and Gmail address for FLask-Mail to function.
- **helpers.py**, where I started to keep helpers functions from Finance, to finally use it much more for the recurring SQLite queries.
- **ptits_oignons.db** contains users, vegetables, orders, and orders items. It is queried differently by users and admin.

###### Documentations and notes
Hereunder is a list of the read documentations that helped greatly my beginner skills to put up this webapp:
- (Datetime module doc)[https://docs.python.org/3/library/datetime.html], teaches you how to NOT format your dates.
- (XlsxWriter documentation)[https://xlsxwriter.readthedocs.io/index.html], is a great module to output Excel spreadsheets, for those who rely on them - like me.
- (Flask-Mail)[https://pythonhosted.org/Flask-Mail/], as it is the easiest module to perform simple mailing tasks on Flask. Note that an async version of the module is available for biggest tasks at (Flask-Mailing)[https://marktennyson.github.io/flask-mailing/].
- (Flask-Sessions)[https://flask-session.readthedocs.io/en/latest/], a staple, I trust, to handle any Flask app with Login / Logout possibilities.
- (Flask-GoogleMaps)[https://flask-googlemaps.com/], allowing to train API management with minimal code requirements (requires nevertheless a Google account to enable the API)

Les Petits Oignons includes a corrected version of the last module, as it is available with a JS typo.
Correction note on Github is available (here)[https://github.com/flask-extensions/Flask-GoogleMaps/pull/143/commits/c5acee98c2f55de54d0491ff151f2d909620fd80].

###### Thanks
Developped on my own.
Hence big thanks @CS50, @dmalan, @brianyu28 for the amazing content !
Truly caught by the classes, and seeing the results of top-level teaching.