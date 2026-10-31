# Copyright © 2026 Vincent Fournet
"""User-facing errors.

Every refusal carries a stable ``code`` and parameters, and is rendered in
French or English. A message always says what went wrong, whether anything
was saved, and what to do next (UX 06). Codes are part of the public
contract: the interface may react to them (for example, open the existing
expense when a duplicate invoice is detected).
"""
from __future__ import annotations

from typing import Any

# code: (French, English). ``{name}`` placeholders are filled from params.
MESSAGES: dict[str, tuple[str, str]] = {
    # Generic input validation
    "amount_required": ("Montant obligatoire. Rien n'a été enregistré.", "An amount is required. Nothing was saved."),
    "amount_format": ("Montant illisible : utilisez des chiffres et au plus deux décimales (ex. 12,50). Rien n'a été enregistré.", "Unreadable amount: use digits and at most two decimals (e.g. 12.50). Nothing was saved."),
    "amount_ambiguous": ("Montant ambigu (« 1.250 » peut signifier 1,25 € ou 1 250 €). Corrigez le fichier ou la saisie.", "Ambiguous amount (\"1.250\" could be 1.25 or 1,250). Fix the file or the entry."),
    "amount_zero": ("Le montant ne peut pas être nul. Rien n'a été enregistré.", "The amount cannot be zero. Nothing was saved."),
    "amount_negative": ("Le montant doit être positif. Pour un remboursement, utilisez un ajustement. Rien n'a été enregistré.", "The amount must be positive. For a refund, use an adjustment. Nothing was saved."),
    "amount_too_large": ("Montant trop élevé. Rien n'a été enregistré.", "Amount too large. Nothing was saved."),
    "date_format": ("Date invalide : format attendu AAAA-MM-JJ. Rien n'a été enregistré.", "Invalid date: expected YYYY-MM-DD. Nothing was saved."),
    "date_range": ("Date hors de la plage acceptée (2000–2100). Rien n'a été enregistré.", "Date outside the accepted range (2000–2100). Nothing was saved."),
    "text_required": ("Le champ « {field} » est obligatoire. Rien n'a été enregistré.", "The field \"{field}\" is required. Nothing was saved."),
    "text_too_long": ("Le champ « {field} » est trop long ({limit} caractères maximum).", "The field \"{field}\" is too long ({limit} characters maximum)."),
    "text_invalid": ("Le champ « {field} » contient des caractères non autorisés.", "The field \"{field}\" contains characters that are not allowed."),
    "choice_invalid": ("Valeur non reconnue pour « {field} ».", "Unrecognised value for \"{field}\"."),
    "currency_unsupported": ("Cette version calcule uniquement en euros (EUR). Les données en {currency} sont bloquées pour les calculs : aucune conversion automatique n'est faite.", "This version only computes in euros (EUR). Data in {currency} is blocked from calculations: no automatic conversion is made."),
    # Accounts and sign-in
    "login_required": ("Session expirée ou absente : reconnectez-vous. Rien n'a été enregistré.", "Your session has expired: sign in again. Nothing was saved."),
    "login_failed": ("Identifiant ou mot de passe incorrect.", "Wrong user name or password."),
    "login_locked": ("Trop d'essais depuis cette adresse : réessayez dans quelques minutes.", "Too many attempts from this address: try again in a few minutes."),
    "totp_required": ("Saisissez le code à six chiffres de votre application d'authentification.", "Enter the six-digit code from your authenticator app."),
    "totp_invalid": ("Code incorrect ou déjà utilisé. Attendez le code suivant.", "Wrong or already used code. Wait for the next one."),
    "mfa_expired": ("La vérification a expiré (5 minutes) : saisissez à nouveau votre identifiant et votre mot de passe.", "The check expired (5 minutes): enter your user name and password again."),
    "password_wrong": ("Mot de passe actuel incorrect : rien n'a été modifié.", "Current password is wrong: nothing was changed."),
    "mfa_setup_expired": ("L'activation a expiré (10 minutes) : recommencez depuis le début. Rien n'a été modifié.", "Setup expired (10 minutes): start again. Nothing was changed."),
    "mfa_already": ("La double authentification est déjà activée sur ce compte.", "Two-factor authentication is already on for this account."),
    "mfa_not_enabled": ("La double authentification n'est pas activée sur ce compte.", "Two-factor authentication is not on for this account."),
    "api_key_name": ("Donnez un nom à la clé (1 à 60 caractères), par exemple « Home Assistant ».", "Name the key (1 to 60 characters), for example \"Home Assistant\"."),
    "api_key_limit": ("Dix clés actives au maximum : révoquez-en une avant d'en créer une autre.", "Ten active keys at most: revoke one before creating another."),
    "setup_done": ("Le compte administrateur existe déjà : connectez-vous.", "The administrator account already exists: sign in."),
    "username_invalid": ("Identifiant : 3 à 40 caractères parmi lettres, chiffres, point, tiret et soulignement.", "User name: 3 to 40 characters among letters, digits, dot, dash and underscore."),
    "password_too_short": ("Mot de passe trop court : {min} caractères minimum.", "Password too short: at least {min} characters."),
    "password_mismatch": ("Les deux mots de passe ne correspondent pas.", "The two passwords do not match."),
    "csrf_failed": ("Requête refusée par sécurité (jeton de formulaire absent ou expiré). Rechargez la page.", "Request refused for safety (missing or expired form token). Reload the page."),
    # Access
    "forbidden": ("Droits insuffisants pour cette action. Demandez à un administrateur de vous donner accès.", "You do not have permission for this action. Ask an administrator for access."),
    "forbidden_property": ("Ce bien n'existe pas ou ne vous est pas accessible.", "This property does not exist or is not available to you."),
    "forbidden_documents": ("L'accès aux justificatifs PDF ne vous a pas été accordé.", "Access to PDF documents has not been granted to you."),
    "demo_read_only": ("La démonstration est en lecture seule pour les lecteurs.", "The demo is read-only for readers."),
    # Objects
    "not_found": ("Élément introuvable : il a peut-être été supprimé ou archivé. Actualisez la page.", "Item not found: it may have been deleted or archived. Refresh the page."),
    "stale_revision": ("Cet élément a été modifié entre-temps. Actualisez puis recommencez : rien n'a été enregistré.", "This item was changed in the meantime. Refresh and try again: nothing was saved."),
    "archived": ("Cet élément est archivé. Désarchivez-le avant de le modifier.", "This item is archived. Unarchive it before editing."),
    "property_archived": ("Le bien « {name} » est archivé : désarchivez-le pour y ajouter des données.", "The property \"{name}\" is archived: unarchive it to add data."),
    "category_kind": ("La catégorie « {name} » ne correspond pas à ce type d'écriture.", "The category \"{name}\" does not match this kind of entry."),
    "category_in_use": ("Cette catégorie est utilisée par {count} écriture(s) : archivez-la plutôt que de la supprimer.", "This category is used by {count} entries: archive it instead of deleting it."),
    "category_builtin": ("Les catégories fournies ne peuvent pas être supprimées ; vous pouvez les renommer ou les archiver.", "Built-in categories cannot be deleted; you can rename or archive them."),
    # Stays
    "stay_dates": ("La date de départ doit être après la date d'arrivée (au moins une nuit).", "The departure date must be after the arrival date (at least one night)."),
    "stay_unavailable": ("Le bien est indiqué indisponible du {start} au {end} : vérifiez les dates ou la période d'indisponibilité.", "The property is marked unavailable from {start} to {end}: check the dates or the unavailability period."),
    "stay_overlap": ("Ce séjour chevauche « {label} » ({start} → {end}) sur le même bien. Confirmez si c'est voulu.", "This stay overlaps \"{label}\" ({start} → {end}) on the same property. Confirm if this is intended."),
    "stay_external_ref_exists": ("Un séjour avec la référence « {ref} » existe déjà sur ce bien. Ouvrez-le au lieu d'en créer un second.", "A stay with reference \"{ref}\" already exists on this property. Open it instead of creating a second one."),
    "stay_linked": ("Ce séjour est lié à {count} paiement(s) ou ventilation(s) : annulez-le au lieu de le supprimer.", "This stay is linked to {count} payments or allocations: cancel it instead of deleting it."),
    "stay_not_manual": ("Seul un séjour saisi manuellement peut être supprimé ; un séjour importé s'annule via l'annulation de son import.", "Only a manually entered stay can be deleted; an imported stay is removed by rolling back its import."),
    # Entries and payments
    "lines_total_mismatch": ("Le total des prestations est de {lines}, mais la facture indique {total}. Corrigez une ligne ou ajoutez un ajustement justifié.", "The service lines total {lines}, but the invoice says {total}. Fix a line or add a justified adjustment."),
    "adjustment_note_required": ("Un ajustement doit être justifié par une note.", "An adjustment must be explained with a note."),
    "allocation_exceeds": ("La ventilation dépasse le montant de {what} ({total}). Rien n'a été enregistré.", "The allocation exceeds the amount of {what} ({total}). Nothing was saved."),
    "allocation_stay_property": ("Une prestation ne peut être affectée qu'à un séjour du même bien.", "A service can only be allocated to a stay of the same property."),
    "allocation_line_required": ("Cette dépense est détaillée en prestations : choisissez la prestation à affecter.", "This expense is broken down into services: choose which service to allocate."),
    "loan_split_mismatch": ("Capital + intérêts + assurance ({split}) doit être égal à la mensualité ({total}).", "Principal + interest + insurance ({split}) must equal the instalment ({total})."),
    "loan_split_category": ("La décomposition capital/intérêts/assurance est réservée aux remboursements d'emprunt.", "The principal/interest/insurance breakdown is only for loan repayments."),
    "payout_exceeds": ("Ce versement dépasse ce qui reste à recevoir pour ce séjour ({remaining} sur {expected} attendus). Corrigez d'abord les montants du séjour si le versement est juste. Rien n'a été enregistré.", "This payout exceeds what is left to receive for this stay ({remaining} of {expected} expected). If the payout is right, correct the stay amounts first. Nothing was saved."),
    "stay_cancel_route": ("Pour annuler un séjour, utilisez « Annuler le séjour » : il demande le montant éventuellement conservé.", "To cancel a stay, use \"Cancel the stay\": it asks for any amount retained."),
    "stay_restore_route": ("Pour rétablir un séjour annulé, utilisez « Rétablir le séjour ».", "To bring back a cancelled stay, use \"Restore the stay\"."),
    "stay_already_cancelled": ("Ce séjour est déjà annulé.", "This stay is already cancelled."),
    "stay_not_cancelled": ("Ce séjour n'est pas annulé : rien à rétablir.", "This stay is not cancelled: nothing to restore."),
    "cancel_commission_too_high": ("La commission conservée ne peut pas dépasser le montant conservé.", "The retained commission cannot exceed the retained amount."),
    "cancel_received_too_high": ("{received} ont déjà été reçus pour ce séjour : le montant conservé net de commission ne peut pas être inférieur. Supprimez d'abord le versement s'il a été remboursé.", "{received} were already received for this stay: the retained amount net of commission cannot be lower. Delete the payout first if it was refunded."),
    "payment_exceeds": ("Ce paiement dépasse le reste à payer ({remaining}). Rien n'a été enregistré.", "This payment exceeds the remaining amount ({remaining}). Nothing was saved."),
    "payment_links_mismatch": ("La répartition du paiement ({links}) doit être égale à son montant ({total}).", "The payment breakdown ({links}) must equal its amount ({total})."),
    "payment_direction": ("Un paiement versé concerne une dépense ; une somme reçue concerne un séjour ou une recette.", "An outgoing payment relates to an expense; a received amount relates to a stay or an income."),
    "supersede_invalid": ("La dépense « {label} » ne peut pas être rapprochée : {reason}.", "The expense \"{label}\" cannot be reconciled: {reason}."),
    "superseded": ("Cette dépense a été remplacée par une facture lors d'un rapprochement : modifiez la facture.", "This expense was replaced by an invoice during reconciliation: edit the invoice."),
    "duplicate_operation": ("Opération déjà enregistrée (double clic détecté) : aucune seconde écriture n'a été créée.", "Operation already saved (double click detected): no second entry was created."),
    # Documents
    "pdf_too_large": ("PDF trop volumineux : 8 Mio maximum. Rien n'a été enregistré.", "PDF too large: 8 MiB maximum. Nothing was saved."),
    "pdf_invalid": ("Ce fichier n'est pas un PDF valide (corrompu, tronqué ou d'un autre type). Rien n'a été enregistré.", "This file is not a valid PDF (corrupted, truncated or another type). Nothing was saved."),
    "pdf_encrypted": ("PDF protégé par mot de passe : enregistrez une copie non protégée puis réessayez.", "Password-protected PDF: save an unprotected copy and try again."),
    "pdf_active_content": ("Ce PDF contient du contenu actif ou des fichiers intégrés (scripts, pièces jointes) : il est refusé par sécurité.", "This PDF contains active content or embedded files (scripts, attachments): it is refused for safety."),
    "pdf_too_complex": ("PDF trop complexe ou trop long (200 pages maximum) : il demanderait trop de ressources.", "PDF too complex or too long (200 pages maximum): it would need too many resources."),
    "document_duplicate": ("Cette facture existe déjà ({reason}). Ouvrez la dépense existante au lieu de l'importer à nouveau.", "This invoice already exists ({reason}). Open the existing expense instead of importing it again."),
    "document_already_attached": ("Ce justificatif est déjà joint à cette dépense.", "This document is already attached to this expense."),
    "document_integrity": ("Le fichier archivé ne correspond plus à son empreinte : il a été modifié ou endommagé. Restaurez une sauvegarde.", "The stored file no longer matches its fingerprint: it was modified or damaged. Restore a backup."),
    "document_missing_blob": ("Le fichier PDF est introuvable dans le stockage privé. Restaurez une sauvegarde.", "The PDF file is missing from private storage. Restore a backup."),
    "preview_expired": ("La prévisualisation a expiré (10 minutes) ou a déjà été utilisée : rien n'a été enregistré. Relancez l'import.", "The preview expired (10 minutes) or was already used: nothing was saved. Start the import again."),
    "preview_stale": ("Les données ont changé depuis la prévisualisation : rien n'a été enregistré. Relancez la prévisualisation.", "Data changed since the preview: nothing was saved. Run the preview again."),
    "preview_limit": ("Trop de prévisualisations en cours : terminez ou attendez quelques minutes.", "Too many previews in progress: finish one or wait a few minutes."),
    "confirmation_required": ("Confirmation explicite nécessaire avant d'enregistrer.", "Explicit confirmation is required before saving."),
    "upload_missing": ("Fichier introuvable ou expiré : envoyez-le à nouveau.", "File not found or expired: upload it again."),
    "upload_too_large": ("Fichier trop volumineux ({limit} maximum).", "File too large ({limit} maximum)."),
    "storage_full": ("Espace disque insuffisant : rien n'a été enregistré. Libérez de l'espace puis recommencez.", "Not enough disk space: nothing was saved. Free some space and try again."),
    "storage_failed": ("L'enregistrement a échoué ({detail}) : l'état précédent a été conservé, rien n'a été modifié.", "Saving failed ({detail}): the previous state was kept, nothing was changed."),
    # Imports
    "csv_empty": ("Fichier CSV vide.", "Empty CSV file."),
    "csv_encoding": ("Encodage non reconnu : enregistrez le fichier en UTF-8.", "Unrecognised encoding: save the file as UTF-8."),
    "csv_no_header": ("Aucune ligne d'en-tête trouvée dans le fichier.", "No header row found in the file."),
    "csv_too_many_rows": ("Fichier trop long ({limit} lignes maximum par import).", "File too long ({limit} rows maximum per import)."),
    "csv_mapping_missing": ("Associez au moins les colonnes obligatoires : {fields}.", "Map at least the required columns: {fields}."),
    "csv_mapping_unknown": ("La colonne « {column} » n'existe pas dans ce fichier.", "The column \"{column}\" does not exist in this file."),
    "import_unknown_format": ("Format non reconnu : {detail}. Aucune donnée n'a été lue ni enregistrée. Consultez la liste des formats pris en charge.", "Unrecognised format: {detail}. No data was read or saved. See the list of supported formats."),
    "import_blocking_errors": ("Le fichier contient {count} erreur(s) bloquante(s) : corrigez-les avant de confirmer.", "The file contains {count} blocking errors: fix them before confirming."),
    "import_nothing": ("Rien à importer : toutes les lignes sont déjà présentes ou en attente.", "Nothing to import: every row is already present or waiting for review."),
    "import_already": ("Ce fichier a déjà été importé le {date}. Rien n'a été modifié.", "This file was already imported on {date}. Nothing was changed."),
    "rollback_last_only": ("Seul le dernier import peut être annulé automatiquement.", "Only the latest import can be rolled back automatically."),
    "rollback_modified": ("Des éléments créés par cet import ont été modifiés depuis : annulation automatique refusée pour ne rien perdre. Corrigez-les à la main.", "Items created by this import were modified since: automatic rollback refused so nothing is lost. Fix them by hand."),
    # Backup
    "backup_invalid": ("Sauvegarde invalide : {detail}. Rien n'a été restauré.", "Invalid backup: {detail}. Nothing was restored."),
    "backup_schema_newer": ("Cette sauvegarde vient d'une version plus récente (schéma {schema}) : mettez à jour Rental Cockpit avant de la restaurer.", "This backup comes from a newer version (schema {schema}): update Rental Cockpit before restoring it."),
    "restore_not_verified": ("Vérifiez d'abord la sauvegarde (copie de recette) avant de la restaurer.", "Check the backup first (test copy) before restoring it."),
    "purge_confirmation": ("Pour supprimer définitivement, tapez exactement « {word} ».", "To delete permanently, type exactly \"{word}\"."),
}

# Generic fallback, never shown with technical details.
UNKNOWN = ("Erreur inattendue : rien n'a été enregistré. Le diagnostic peut aider à comprendre.", "Unexpected error: nothing was saved. The diagnostics page may help.")


class RCError(Exception):
    """A refusal explained to the user."""

    def __init__(self, code: str, **params: Any) -> None:
        super().__init__(code)
        self.code = code
        self.params = params

    def message(self, lang: str = "fr") -> str:
        return render(self.code, self.params, lang)

    def as_dict(self, lang: str = "fr") -> dict[str, Any]:
        return {"code": self.code, "message": self.message(lang), "params": _plain(self.params)}


def render(code: str, params: dict[str, Any] | None = None, lang: str = "fr") -> str:
    fr, en = MESSAGES.get(code, UNKNOWN)
    template = fr if lang == "fr" else en
    try:
        return template.format(**(params or {}))
    except (KeyError, IndexError, ValueError):
        return template


def from_value_error(exc: ValueError, field: str | None = None) -> RCError:
    """Turn a ``ValueError("amount_format")`` raised by a helper into an RCError."""
    code = str(exc.args[0]) if exc.args else "unknown"
    if code not in MESSAGES:
        code = "choice_invalid"
    return RCError(code, field=field or "")


def _plain(params: dict[str, Any]) -> dict[str, Any]:
    return {key: value if isinstance(value, (str, int, float, bool, type(None))) else str(value) for key, value in params.items()}
