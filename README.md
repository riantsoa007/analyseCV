# ANALYSE CV - MVC + SQLAlchemy (style Laravel)

Application Flask avec Jinja2, structure MVC et ORM SQLAlchemy.

## Structure du projet

```
CRUD Flask/
├── app.py                      # Point d'entree
├── config.py                   # Configuration (URI SQLAlchemy)
├── extensions.py               # Instance db (SQLAlchemy)
├── database.py                 # Creation BDD + tables
├── controllers/                # Toute la logique CRUD (requetes ORM)
│   └── produit_controller.py
├── models/                     
│   └── produit.py
├── routes/                     # URLs (Blueprint)
│   └── produit_routes.py
└── templates/                  # Vues Jinja2
```

## Modele vs Controller (style Laravel)

| Laravel | Ce projet |
|---------|-----------|
| `Produit.php` — `$fillable`, relations | `models/produit.py` — colonnes SQLAlchemy |
| `ProduitController.php` — logique | `controllers/produit_controller.py` — `Produit.query`, `db.session` |

Le modele ne contient **aucune methode metier** ; le controller execute les requetes ORM.

## Installation

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

## Details des dependances (`requirements.txt` lignes 2-3)

### `Flask-SQLAlchemy==3.1.1`

Ce package integre SQLAlchemy avec Flask et fournit l'objet `db` utilise dans toute l'application.

Utilisation dans ce projet :
- Dans `extensions.py` : `db = SQLAlchemy()` cree l'instance ORM partagee.
- Dans `database.py` : `db.init_app(app)` rattache l'ORM a la configuration Flask.
- Dans `database.py` : `db.create_all()` cree les tables a partir des modeles.
- Dans `models/produit.py` : `class Produit(db.Model)` definit la table et les colonnes.
- Dans `controllers/produit_controller.py` : les lectures/ecritures ORM utilisent `Produit.query` et `db.session`.

Pourquoi c'est important :
- Evite d'ecrire du SQL brut pour les operations CRUD courantes.
- Garde des modeles propres et proches du style Laravel.
- Rend le code plus simple a maintenir et a faire evoluer.

### `PyMySQL==1.1.1`

C'est le pilote MySQL utilise par SQLAlchemy pour connecter Python a votre serveur MySQL.

Utilisation dans ce projet :
- Dans `config.py`, l'URI commence par `mysql+pymysql://...`.
- La partie `pymysql` indique a SQLAlchemy d'utiliser PyMySQL comme driver backend.
- Il est utilise a la fois pour creer la base (`ensure_database_exists`) et pour executer les operations ORM.

Pourquoi c'est important :
- Sans PyMySQL, SQLAlchemy ne peut pas ouvrir de connexion MySQL.
- Il permet la communication avec votre MySQL local (`root`, mot de passe vide, base `crudflask`).

### Comment ils fonctionnent ensemble

- `Flask-SQLAlchemy` = ORM + couche d'integration Flask.
- `PyMySQL` = connecteur MySQL bas niveau.
- Flux global : controller -> ORM SQLAlchemy -> driver PyMySQL -> serveur MySQL.

MySQL : utilisateur `root`, mot de passe vide, base `crudflask`.
