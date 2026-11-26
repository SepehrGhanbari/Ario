# Ario Kladje — research enrollment only

IPng granted use of Kladje for synthetic research, maximum 24 requests per day. The Witness Network testing list still needs the specific log origin and public vkey. This package prepares those values; it does not contact Kladje or submit any registration.

On the desktop test computer (not the production signer), with Python and cryptography installed, run `python enroll.py init`. Choose a private passphrase of at least 12 bytes. Keep it and the encrypted `research-log.private.pem` in the local `Ario-Kladje-Research-v1` folder; do not upload or commit them. Back up the encrypted PEM securely. `show` recovers the same public vkey; `init` never overwrites an existing directory. If necessary install `cryptography==46.0.4`.

The founder should personally send the public vkey and testing-list request to participate@lists.witness-network.org using a chosen public contact address. The mailing list is publicly archived and explicitly prefers human communication. After acceptance, `python enroll.py check` checks exact origin/key membership through the official HTTPS testing list. This does not prove that the witness has loaded the entry or that it is fresh.

Offline test command: `python -B -m unittest -v`. Four test methods passed in isolated local Python using cryptography 46.0.4; test identities are temporary and must never be enrolled. No live checkpoint publication, registration, rollback test, or evidence admission. No real Ario keys, trust activation, Genesis or production changes.

Sources: https://witness-network.org/participate/ ; https://testing.witness-network.org/log-list.1 ; https://ipng.ch/s/ct/ ; https://c2sp.org/signed-note ; https://c2sp.org/tlog-checkpoint .
