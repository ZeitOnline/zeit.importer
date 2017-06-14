=========
K4-Import
=========

Wandelt XML-Dateien aus dem K4-Redaktionssystem um ins vivi-Format und
speichert sie im DAV ab.

Der Vorgang wird angestoßen indem von K4 aus Dateien per SFTP abgeladen werden
und anschließend unser ``k4import`` Skript aufgerufen wird.

Eine Beispiel-Konfigurationsdatei liegt in ``k4import-example.ini``.


Tests laufen lassen
===================

Mit `tox`_ und pytest. ``tox`` ggfs. installieren (z.B. via ``pip install tox``)
und dann einfach ``tox`` aufrufen.

.. _`tox`: http://tox.readthedocs.io/


Deployment
==========

* Egg erstellen mit zest.releaser ``fullrelease``, und nach
  http://devpi.zeit.de:4040/zeit/default/ hochladen.
* Zunächst im environment ``zeit-staging`` die Versionsnummer hochziehen und
  mit ``knife environment from file environments/zeit-staging.json`` hochladen.
  Dann chef laufen lassen und Abnahme abwarten.
* Im Chef-Kochbuch ``zeit-vivi`` in ``attributes/default.rb`` die Versionsnummer
  ``vivi/k4import/version`` hochziehen, hochladen, Chef laufen lassen.
