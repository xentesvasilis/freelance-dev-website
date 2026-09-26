"""Labels for the private CRM; public commercial content remains unchanged."""
from .content import tr

LABELS = {
    "proposal": "Πρόταση", "proposal_sent": "Η πρόταση στάλθηκε", "accepted": "Αποδεκτό",
    "in_development": "Σε ανάπτυξη", "waiting_for_client": "Αναμονή πελάτη", "testing": "Έλεγχος",
    "delivered": "Παραδόθηκε", "maintenance": "Συντήρηση", "on_hold": "Σε αναστολή", "cancelled": "Ακυρώθηκε",
    "low": "Χαμηλή", "normal": "Κανονική", "high": "Υψηλή", "urgent": "Επείγουσα",
    "Projects": "Projects", "New project": "Νέο project", "Project detail": "Στοιχεία project",
    "Title": "Τίτλος", "Client name": "Όνομα πελάτη", "Email": "Email", "Phone": "Τηλέφωνο",
    "Company": "Εταιρεία", "Industry": "Κλάδος", "Summary": "Περιγραφή", "Internal notes": "Εσωτερικές σημειώσεις",
    "Package": "Πακέτο", "Quoted price (EUR)": "Προσφορά (EUR)", "Status": "Κατάσταση", "Priority": "Προτεραιότητα",
    "Target start": "Προγραμματισμένη έναρξη", "Target delivery": "Προγραμματισμένη παράδοση",
    "Save project": "Αποθήκευση project", "Update status": "Αλλαγή κατάστασης", "Edit project": "Επεξεργασία project",
    "Convert to Project": "Μετατροπή σε Project", "Open project": "Άνοιγμα project",
    "Confirm creation of a private project. The lead and its status will stay unchanged.": "Επιβεβαιώνω τη δημιουργία ιδιωτικού project. Το Lead και η κατάστασή του δεν αλλάζουν.",
    "Source lead": "Αρχικό Lead", "Manual creation": "Χειροκίνητη δημιουργία", "Client": "Πελάτης",
    "Project": "Project", "Scope": "Αντικείμενο", "Timeline (UTC)": "Χρονολόγιο (UTC)",
    "Created": "Δημιουργήθηκε", "Updated": "Ενημερώθηκε", "Source": "Προέλευση",
    "Active projects": "Ενεργά projects", "Proposals": "Προτάσεις", "Projects requiring attention": "Projects που χρειάζονται προσοχή",
    "No projects requiring attention.": "Δεν υπάρχουν projects που χρειάζονται προσοχή.",
    "No projects found.": "Δεν βρέθηκαν projects.", "Search": "Αναζήτηση", "All": "Όλα", "Filter": "Φίλτρα",
    "Previous": "Προηγούμενη", "Next": "Επόμενη", "Overdue": "Εκπρόθεσμο", "Due within 7 days": "Παράδοση εντός 7 ημερών",
    "Project saved.": "Το project αποθηκεύτηκε.", "Status updated.": "Η κατάσταση ενημερώθηκε.",
    "Use a nonnegative amount with at most two decimal places, e.g. 1700.50.": "Χρησιμοποιήστε μη αρνητικό ποσό με έως δύο δεκαδικά, π.χ. 1700.50.",
    "Delivery must not be before start.": "Η παράδοση δεν μπορεί να προηγείται της έναρξης.",
    "Please correct the fields below.": "Διορθώστε τα παρακάτω πεδία.",
}


def crm_label(key):
    return tr({"en": key.replace("_", " ").capitalize() if key in LABELS and key.islower() else key,
               "el": LABELS.get(key, key)})
