"""Shared bilingual copy and commercial configuration; no template-level translations."""
from flask import g


def bi(en, el):
    return {"en": en, "el": el}


def tr(value):
    value = TEXT.get(value, value) if isinstance(value, str) else value
    return value.get(getattr(g, "lang", "en"), value.get("en", "")) if isinstance(value, dict) else value


TEXT = {
    "home": bi("Home", "Αρχική"), "services": bi("Services", "Υπηρεσίες"),
    "industries": bi("Industries", "Κλάδοι"), "portfolio": bi("Selected work", "Έργα"),
    "pricing": bi("Pricing", "Πακέτα"), "process": bi("Process", "Διαδικασία"),
    "about": bi("About", "Σχετικά"), "contact": bi("Contact", "Επικοινωνία"),
    "privacy": bi("Privacy Policy", "Πολιτική απορρήτου"), "terms": bi("Terms", "Όροι χρήσης"),
    "book_call": bi("Book a consultation", "Κλείσε δωρεάν συζήτηση"),
    "book-call": bi("Let's discuss your project", "Ας συζητήσουμε το project σου"),
    "view_services": bi("View services", "Δες τις υπηρεσίες"),
    "start_project": bi("Tell me about your project", "Πες μου για το project σου"),
    "view_github": bi("View GitHub", "Δες το GitHub"),
    "eyebrow": bi("INDEPENDENT DEVELOPMENT · BUILT AROUND YOUR BUSINESS", "ΑΝΕΞΑΡΤΗΤΗ ΑΝΑΠΤΥΞΗ · ΜΕ ΒΑΣΗ ΤΗΝ ΕΠΙΧΕΙΡΗΣΗ ΣΟΥ"),
    "hero": bi("Websites and web applications that make your business easier to run.", "Ιστοσελίδες και web εφαρμογές που κάνουν τη δουλειά της επιχείρησής σας πιο απλή."),
    "hero_text": bi("Professional websites. Seamless booking. Less manual work. I build custom web applications and business automations that connect your online presence to the way you work.", "Επαγγελματικές ιστοσελίδες, online booking και λιγότερη χειροκίνητη δουλειά. Αναπτύσσω web εφαρμογές και αυτοματισμούς που συνδέουν την online παρουσία σας με την καθημερινή λειτουργία της επιχείρησης."),
    "hero_note": bi("A short, free discovery call. A clear next step.", "Μια σύντομη, δωρεάν συζήτηση. Ένα ξεκάθαρο επόμενο βήμα."),
    "system_label": bi("YOUR BUSINESS, CONNECTED", "Η ΕΠΙΧΕΙΡΗΣΗ ΣΑΣ, ΣΥΝΔΕΔΕΜΕΝΗ"),
    "system_title": bi("From first visit to a simpler workflow.", "Από την πρώτη επίσκεψη σε μια απλούστερη ροή εργασίας."),
    "system_steps": bi(["Website", "Enquiry", "Booking", "Your dashboard"], ["Ιστοσελίδα", "Ενδιαφέρον", "Ραντεβού", "Πίνακας διαχείρισης"]),
    "system_note": bi("Designed as one considered system.", "Σχεδιασμένα ως ένα ολοκληρωμένο σύστημα."),
    "what_build": bi("A website is the starting point.", "Η ιστοσελίδα είναι η αρχή."),
    "what_intro": bi("The right tools help people find you, get in touch and take the next step — while giving you less to manage.", "Τα σωστά εργαλεία βοηθούν τον πελάτη να σας βρει, να επικοινωνήσει και να κάνει το επόμενο βήμα, με λιγότερη διαχείριση για εσάς."),
    "industries_title": bi("Built for people who mean business.", "Για επαγγελματίες με ουσιαστικές ανάγκες."),
    "industries_intro": bi("Different businesses need different workflows. The solution starts with how yours operates.", "Κάθε επιχείρηση χρειάζεται διαφορετικές ροές εργασίας. Η λύση ξεκινά από τον τρόπο που λειτουργεί η δική σας."),
    "why_title": bi("Direct collaboration. Thoughtful engineering.", "Άμεση συνεργασία. Προσεγμένη ανάπτυξη."),
    "pricing_title": bi("A clear starting point for your investment.", "Μια ξεκάθαρη αφετηρία για την επένδυσή σας."),
    "pricing_intro": bi("Three packages, shaped around the work you need done. We agree the scope and final quote before development begins.", "Τρία πακέτα, προσαρμοσμένα στις ανάγκες σας. Συμφωνούμε το εύρος και την τελική προσφορά πριν ξεκινήσει η ανάπτυξη."),
    "starting": bi("Starting from", "Από"), "month": bi("/month", "/μήνα"),
    "maintenance": bi("Maintenance", "Συντήρηση"), "discuss_package": bi("Discuss this package", "Συζήτησε αυτό το πακέτο"),
    "popular": bi("CONNECT YOUR WORKFLOW", "ΟΡΓΑΝΩΣΕ ΤΗ ΡΟΗ ΣΟΥ"),
    "cost_note": bi("Domain, hosting, third-party subscriptions and paid external services are separate. Final scope and any applicable taxes are confirmed in your written quote.", "Domain, hosting, συνδρομές τρίτων και εξωτερικές υπηρεσίες επί πληρωμή χρεώνονται χωριστά. Το τελικό εύρος και τυχόν φόροι επιβεβαιώνονται στη γραπτή προσφορά."),
    "maintenance_text": bi("Depending on the agreed package, maintenance can cover dependency and security updates, monitoring, backup oversight, minor content updates, small technical fixes, deployment maintenance and basic support. Support scope and response arrangements are agreed in writing.", "Ανάλογα με το συμφωνημένο πακέτο, η συντήρηση μπορεί να καλύπτει ενημερώσεις εξαρτήσεων και ασφάλειας, παρακολούθηση, εποπτεία αντιγράφων ασφαλείας, μικρές αλλαγές περιεχομένου, τεχνικές διορθώσεις, συντήρηση deployment και βασική υποστήριξη. Το εύρος και οι χρόνοι υποστήριξης συμφωνούνται γραπτώς."),
    "new_features": bi("New features and significant design/development changes are quoted separately.", "Νέες λειτουργίες και σημαντικές αλλαγές σχεδιασμού ή ανάπτυξης κοστολογούνται ξεχωριστά."),
    "external_costs": bi("External costs may include a domain, hosting, a Calendly paid plan, Stripe transaction fees, paid APIs, email provider costs and other SaaS subscriptions.", "Εξωτερικά κόστη μπορεί να περιλαμβάνουν domain, hosting, επί πληρωμή πλάνο Calendly, προμήθειες συναλλαγών Stripe, paid APIs, υπηρεσίες email και άλλες συνδρομές SaaS."),
    "process_title": bi("From a conversation to a working system.", "Από μια συζήτηση σε ένα λειτουργικό σύστημα."),
    "process_intro": bi("Clear scope, visible progress and time to test the details before launch.", "Ξεκάθαρο εύρος, ορατή πρόοδος και χρόνος για δοκιμές πριν από την ανάρτηση."),
    "portfolio_title": bi("How the pieces come together.", "Πώς συνδέονται όλα μεταξύ τους."),
    "portfolio_intro": bi("Explore the architecture and workflows behind a booking and client automation platform.", "Δείτε την αρχιτεκτονική και τις ροές εργασίας μιας πλατφόρμας booking και αυτοματισμού πελατών."),
    "case_label": bi("TECHNICAL CASE STUDY · ANONYMIZED", "ΤΕΧΝΙΚΗ ΠΑΡΟΥΣΙΑΣΗ · ΑΝΩΝΥΜΟΠΟΙΗΜΕΝΗ"),
    "case_title": bi("Booking & Client Automation Platform", "Πλατφόρμα Booking & Αυτοματισμού Πελατών"),
    "case_description": bi("A capability-based technical outline of an accountless booking and payment platform: from a bilingual website and qualification questionnaire to an admin workflow, automated notifications and private payment links. Presented without client-identifying information; a public demo and project assets are not yet available.", "Τεχνική περιγραφή δυνατοτήτων πλατφόρμας booking και πληρωμών χωρίς λογαριασμό πελάτη: από δίγλωσση ιστοσελίδα και φόρμα διερεύνησης αναγκών μέχρι διαχείριση, αυτοματοποιημένες ειδοποιήσεις και ιδιωτικά links πληρωμής. Δεν δημοσιεύονται στοιχεία πελατών· δημόσιο demo και υλικό έργου δεν είναι ακόμη διαθέσιμα."),
    "case_features": bi(["Bilingual, accountless customer flow", "Calendly booking and qualification questionnaire", "Admin dashboard and email notifications", "Secure private payment links and Stripe webhook processing", "Promotion codes, discount support and membership handling"], ["Δίγλωσση εμπειρία χωρίς λογαριασμό πελάτη", "Calendly booking και ερωτηματολόγιο αναγκών", "Πίνακας διαχείρισης και ειδοποιήσεις email", "Ασφαλή ιδιωτικά links πληρωμής και Stripe webhooks", "Κωδικοί προσφορών, εκπτώσεις και διαχείριση συνδρομών"]),
    "future_work": bi("More project stories will be added when they are ready to share.", "Περισσότερα έργα θα προστεθούν όταν είναι έτοιμα για δημοσίευση."),
    "cta_title": bi("Let's discuss your project.", "Ας συζητήσουμε το project σου."),
    "cta_text": bi("Bring an idea, a daily bottleneck or a website that needs a fresh start. We'll work out the next step together.", "Έχεις μια ιδέα, μια καθημερινή δυσκολία ή μια ιστοσελίδα που χρειάζεται ανανέωση; Θα βρούμε μαζί το επόμενο βήμα."),
    "footer_text": bi("Web development & business automation.", "Ανάπτυξη ιστοσελίδων & αυτοματισμοί επιχειρήσεων."),
    "skip": bi("Skip to content", "Μετάβαση στο περιεχόμενο"), "menu": bi("Menu", "Μενού"),
    "language_title": bi("A good conversation starts with the right language.", "Μια καλή συζήτηση ξεκινά στη γλώσσα σου."),
    "language_note": bi("Choose your language. You can change it at any time.", "Επίλεξε γλώσσα. Μπορείς να την αλλάξεις οποιαδήποτε στιγμή."),
    "about_title": bi("Your developer. From discovery to deployment.", "Ο προγραμματιστής σου. Από την ιδέα στο deployment."),
    "about_intro": bi("I'm Vasilis Xentes, and I build modern websites, web applications and business automations for professionals and companies that want a stronger online presence and more efficient digital workflows.", "Είμαι ο Βασίλης Ξεντές και αναπτύσσω σύγχρονες ιστοσελίδες, web εφαρμογές και αυτοματισμούς για επαγγελματίες και επιχειρήσεις που θέλουν να οργανώσουν καλύτερα την online παρουσία και τη λειτουργία τους."),
    "about_body": bi("My focus goes beyond visual design. I build complete solutions that can include online booking, lead qualification forms, automated email workflows, payment systems, dashboards, content management and custom business processes.", "Δεν περιορίζομαι στην κατασκευή μιας όμορφης ιστοσελίδας. Σχεδιάζω ολοκληρωμένες λύσεις με online booking, φόρμες ενδιαφέροντος, αυτοματοποιημένα emails, πληρωμές, dashboards, διαχείριση περιεχομένου και custom workflows."),
    "about_background": bi("With a background in Applied Informatics, I focus on web development and automation using Python, Flask, HTML, CSS, JavaScript, databases and API integrations. Every collaboration starts with understanding the business, followed by planning, development, testing and technical preparation for production.", "Με υπόβαθρο στην Εφαρμοσμένη Πληροφορική, εστιάζω στην ανάπτυξη web και στους αυτοματισμούς με Python, Flask, HTML, CSS, JavaScript, βάσεις δεδομένων και API integrations. Κάθε συνεργασία ξεκινά με κατανόηση των αναγκών, σχεδιασμό, ανάπτυξη, δοκιμές και τεχνική προετοιμασία για production."),
    "contact_title": bi("What would you like to build?", "Τι θα ήθελες να δημιουργήσουμε;"),
    "contact_intro": bi("Share a short brief, or go straight to a discovery call. No account needed.", "Στείλε μια σύντομη περιγραφή ή κλείσε απευθείας μια συζήτηση. Χωρίς δημιουργία λογαριασμού."),
    "form_title": bi("A few details to get started", "Λίγα στοιχεία για να ξεκινήσουμε"),
    "optional": bi("optional", "προαιρετικό"),
    "sensitive": bi("Please do not include medical, legal-case, financial-account or other sensitive personal information in this form.", "Παρακαλώ μην συμπεριλάβετε ιατρικά δεδομένα, στοιχεία νομικών υποθέσεων, χρηματοοικονομικών λογαριασμών ή άλλα ευαίσθητα προσωπικά δεδομένα σε αυτή τη φόρμα."),
    "name": bi("Full name", "Ονοματεπώνυμο"), "email": bi("Email", "Email"),
    "phone": bi("Phone", "Τηλέφωνο"), "company": bi("Company / organization", "Εταιρεία / οργανισμός"),
    "industry": bi("Industry", "Κλάδος"), "requirements": bi("What do you need?", "Τι χρειάζεστε;"),
    "budget": bi("Estimated budget", "Εκτιμώμενο budget"),
    "description": bi("Brief project description", "Σύντομη περιγραφή έργου"),
    "timeframe": bi("Preferred timeframe", "Επιθυμητό χρονοδιάγραμμα"),
    "privacy_accept": bi("I have read the Privacy Policy and agree to my details being used to respond to this enquiry.", "Έχω διαβάσει την Πολιτική απορρήτου και συμφωνώ να χρησιμοποιηθούν τα στοιχεία μου για την απάντηση στο αίτημά μου."),
    "send": bi("Send project brief", "Αποστολή περιγραφής"),
    "select": bi("Select an option", "Επιλέξτε"),
    "required_error": bi("Please complete this field.", "Παρακαλώ συμπληρώστε αυτό το πεδίο."),
    "email_error": bi("Enter a valid email address.", "Συμπληρώστε έγκυρη διεύθυνση email."),
    "choice_error": bi("Select a valid option.", "Επιλέξτε μια έγκυρη επιλογή."),
    "length_error": bi("Please check the length of this field.", "Ελέγξτε το μήκος του πεδίου."),
    "unsafe_error": bi("Please remove line breaks or control characters from this field.", "Αφαιρέστε αλλαγές γραμμής ή χαρακτήρες ελέγχου από αυτό το πεδίο."),
    "form_error": bi("Please review the highlighted fields.", "Ελέγξτε τα επισημασμένα πεδία."),
    "lead_success": bi("Thank you — your brief has been saved. You can now book a discovery call, or I can follow up using your contact details.", "Ευχαριστώ — η περιγραφή σου αποθηκεύτηκε. Μπορείς τώρα να κλείσεις μια συζήτηση ή να περιμένεις επικοινωνία στα στοιχεία που δήλωσες."),
    "booking_intro": bi("A short discovery call to understand your business, discuss the scope and find a sensible next step. You can book directly without submitting a project brief.", "Μια σύντομη συζήτηση για την επιχείρησή σου, το εύρος του έργου και το επόμενο βήμα. Μπορείς να κλείσεις ραντεβού χωρίς να συμπληρώσεις φόρμα έργου."),
    "booking_unconfigured": bi("Online scheduling is being prepared. Email or call me to arrange a consultation.", "Το online booking προετοιμάζεται. Στείλε email ή κάλεσέ με για να οργανώσουμε μια συζήτηση."),
    "load_calendar": bi("Open booking calendar", "Άνοιγμα ημερολογίου"),
    "calendar_privacy": bi("Opening the calendar connects to Calendly, a third-party scheduling service. If you just submitted a brief, your name and email will be prefilled. Review the Privacy Policy before continuing.", "Το άνοιγμα του ημερολογίου συνδέεται με το Calendly, υπηρεσία προγραμματισμού τρίτου. Αν μόλις έστειλες περιγραφή, το όνομα και το email σου θα προσυμπληρωθούν. Διάβασε την Πολιτική απορρήτου πριν συνεχίσεις."),
    "calendar_fallback": bi("Open Calendly in a new tab", "Άνοιγμα Calendly σε νέα καρτέλα"),
    "calendar_loading": bi("Loading calendar… If it does not appear, use the link below.", "Φόρτωση ημερολογίου… Αν δεν εμφανιστεί, χρησιμοποίησε τον παρακάτω σύνδεσμο."),
    "error_400": bi("The request could not be accepted. Please try again.", "Το αίτημα δεν έγινε δεκτό. Δοκιμάστε ξανά."),
    "csrf_error": bi("This form has expired. Reload the page and try again.", "Η φόρμα έληξε. Ανανεώστε τη σελίδα και δοκιμάστε ξανά."),
    "error_403": bi("This page is restricted.", "Η πρόσβαση σε αυτή τη σελίδα είναι περιορισμένη."),
    "error_404": bi("This page could not be found.", "Η σελίδα δεν βρέθηκε."),
    "error_413": bi("This request is too large.", "Το αίτημα είναι υπερβολικά μεγάλο."),
    "error_429": bi("Too many requests. Please try again later.", "Πολλά αιτήματα. Δοκιμάστε ξανά αργότερα."),
    "error_500": bi("Something went wrong. Please try again later.", "Παρουσιάστηκε σφάλμα. Δοκιμάστε ξανά αργότερα."),
    "error_503": bi("We could not save your enquiry. Please try again or contact me by email.", "Δεν ήταν δυνατή η αποθήκευση του αιτήματος. Δοκιμάστε ξανά ή στείλτε email."),
}

PACKAGES = [
    {"name": "Professional Website", "price": "980", "maintenance": "79", "featured": False,
     "summary": bi("A professional presence for independent professionals and small companies.", "Επαγγελματική παρουσία για ελεύθερους επαγγελματίες και μικρές επιχειρήσεις."),
     "features": bi(["Responsive professional website, up to 5 core pages", "Greek or English", "Contact functionality", "Basic SEO and analytics-ready structure", "Deployment setup and initial technical configuration"], ["Responsive επαγγελματική ιστοσελίδα, έως 5 βασικές σελίδες", "Ελληνικά ή Αγγλικά", "Λειτουργία επικοινωνίας", "Βασική δομή SEO και υποδομή για analytics", "Deployment και αρχική τεχνική ρύθμιση"])},
    {"name": "Business Automation", "price": "1,700", "maintenance": "99", "featured": True,
     "summary": bi("Connect your website to your day-to-day business workflow.", "Σύνδεσε την ιστοσελίδα με την καθημερινή λειτουργία της επιχείρησης."),
     "features": bi(["Everything in Professional Website", "Bilingual support where required", "Calendly / appointment booking integration", "Custom enquiry or intake form", "Automated email notifications", "Simple admin / lead view", "Custom workflow configuration and enhanced integrations"], ["Όλα του Professional Website", "Δίγλωσση υποστήριξη όπου απαιτείται", "Calendly / ενσωμάτωση ραντεβού", "Προσαρμοσμένη φόρμα αιτήματος", "Αυτοματοποιημένες ειδοποιήσεις email", "Απλή προβολή διαχείρισης / leads", "Προσαρμογή workflow και ενισχυμένες διασυνδέσεις"])},
    {"name": "Custom Digital Office", "price": "3,000", "maintenance": "119", "featured": False,
     "summary": bi("A tailored system for more involved business requirements. Scope is quoted individually.", "Προσαρμοσμένο σύστημα για πιο σύνθετες ανάγκες. Το εύρος κοστολογείται εξατομικευμένα."),
     "features": bi(["Professional bilingual website", "Booking workflows and custom intake", "Admin dashboard", "Advanced automation and custom business logic", "Payment integration where applicable", "API integrations where required", "Production deployment setup"], ["Επαγγελματική δίγλωσση ιστοσελίδα", "Ροές booking και προσαρμοσμένες φόρμες", "Πίνακας διαχείρισης", "Προηγμένοι αυτοματισμοί και επιχειρησιακή λογική", "Πληρωμές όπου απαιτούνται", "API integrations όπου χρειάζονται", "Ρύθμιση production deployment"])}
]

CONTENT = {
    "capabilities": [
        (bi("Professional websites", "Επαγγελματικές ιστοσελίδες"), bi("A considered digital home for your business.", "Μια προσεγμένη ψηφιακή παρουσία για την επιχείρησή σας.")),
        (bi("Booking & appointments", "Booking & ραντεβού"), bi("Make the next available conversation easy to book.", "Εύκολος προγραμματισμός του επόμενου ραντεβού.")),
        (bi("Lead & client intake", "Φόρμες ενδιαφέροντος"), bi("Collect the useful details, without the back-and-forth.", "Τα απαραίτητα στοιχεία, χωρίς ατελείωτες συνεννοήσεις.")),
        (bi("Business automation", "Αυτοματισμοί επιχειρήσεων"), bi("Give repetitive work a reliable process.", "Οργανωμένη διαδικασία για τις επαναλαμβανόμενες εργασίες.")),
        (bi("Payment integrations", "Διασυνδέσεις πληρωμών"), bi("Connect supported payment services to your workflow.", "Σύνδεση υπηρεσιών πληρωμών με τη ροή εργασίας σας.")),
        (bi("Admin dashboards", "Πίνακες διαχείρισης"), bi("Keep enquiries, content and operations in view.", "Οργάνωση αιτημάτων, περιεχομένου και λειτουργιών.")),
        (bi("Custom web applications", "Custom web εφαρμογές"), bi("Software shaped around the way your business works.", "Λογισμικό προσαρμοσμένο στον τρόπο λειτουργίας σας.")),
    ],
    "why": [
        (bi("Your workflow comes first", "Πρώτα η δική σας ροή"), bi("Custom solutions with minimal customer friction, rather than unnecessary steps.", "Προσαρμοσμένες λύσεις που διευκολύνουν τον πελάτη, χωρίς περιττά βήματα.")),
        (bi("One direct conversation", "Άμεση επικοινωνία"), bi("Work directly with the person planning, building and testing your system.", "Συνεργάζεστε με τον άνθρωπο που σχεδιάζει, αναπτύσσει και δοκιμάζει το σύστημα.")),
        (bi("Built to keep working", "Σχεδιασμένο για συνέχεια"), bi("Responsive design, maintainable systems, useful automation and deployment support.", "Responsive σχεδιασμός, συντηρήσιμα συστήματα, ουσιαστικοί αυτοματισμοί και υποστήριξη deployment.")),
    ],
    "services": [
        (bi("Professional Websites", "Επαγγελματικές ιστοσελίδες"), bi("A clear presentation of your business, designed to turn interest into a conversation.", "Ξεκάθαρη παρουσίαση της επιχείρησης, ώστε το ενδιαφέρον να γίνεται επικοινωνία."), bi(["Responsive design", "Company and service presentation", "Bilingual support", "SEO-ready structure", "Contact forms", "Deployment"], ["Responsive σχεδιασμός", "Παρουσίαση εταιρείας και υπηρεσιών", "Δίγλωσση υποστήριξη", "Δομή έτοιμη για SEO", "Φόρμες επικοινωνίας", "Deployment"])),
        (bi("Business Automation", "Αυτοματισμοί επιχειρήσεων"), bi("Less repetitive administration. A more connected way to work.", "Λιγότερη επαναλαμβανόμενη διαχείριση. Περισσότερη οργάνωση στην εργασία."), bi(["Booking workflows", "Automated email", "Lead intake", "Administrative workflows", "Internal dashboards"], ["Ροές booking", "Αυτοματοποιημένα email", "Συλλογή ενδιαφέροντος", "Διοικητικές ροές εργασίας", "Εσωτερικά dashboards"])),
        (bi("Custom Web Applications", "Προσαρμοσμένες web εφαρμογές"), bi("When your requirements go beyond a brochure website.", "Όταν οι ανάγκες σας ξεπερνούν μια ιστοσελίδα παρουσίασης."), bi(["Flask applications", "Client portals", "Admin panels", "Quotation systems", "Booking platforms", "Specialized workflows"], ["Εφαρμογές Flask", "Portals πελατών", "Πίνακες διαχείρισης", "Συστήματα προσφορών", "Πλατφόρμες booking", "Εξειδικευμένες ροές εργασίας"])),
        (bi("Integrations", "Διασυνδέσεις"), bi("Connect the services that make sense for your project, subject to their APIs and plans.", "Σύνδεση υπηρεσιών που ταιριάζουν στο έργο, ανάλογα με τα APIs και τα διαθέσιμα πλάνα τους."), bi(["Calendly", "Stripe", "Email providers", "Business APIs", "Analytics with appropriate privacy configuration"], ["Calendly", "Stripe", "Πάροχοι email", "Επιχειρησιακά APIs", "Analytics με κατάλληλη ρύθμιση απορρήτου"])),
    ],
    "industries": [
        (bi("Healthcare / Medical Practices", "Υγεία / Ιατρεία"), bi(["Practice website, services and doctor / team profiles", "Online appointments and automated notifications", "Publications, conferences and multilingual content"], ["Ιστοσελίδα ιατρείου, υπηρεσίες και προφίλ ιατρών / ομάδας", "Online ραντεβού και αυτοματοποιημένες ειδοποιήσεις", "Δημοσιεύσεις, συνέδρια και πολύγλωσσο περιεχόμενο"]), bi("Detailed medical histories are not collected by default. Systems involving health data require additional privacy and security design; no specialist medical certification is implied.", "Δεν συλλέγεται αναλυτικό ιατρικό ιστορικό από προεπιλογή. Συστήματα με δεδομένα υγείας απαιτούν πρόσθετο σχεδιασμό απορρήτου και ασφάλειας· δεν υπονοείται ειδική ιατρική πιστοποίηση.")),
        (bi("Legal Firms", "Δικηγορικά γραφεία"), bi(["Firm website, lawyers / team and practice areas", "Consultation booking and client enquiry workflows", "Articles, publications and conferences"], ["Ιστοσελίδα γραφείου, δικηγόροι / ομάδα και τομείς δικαίου", "Κράτηση συμβουλευτικής και διαχείριση αιτημάτων", "Άρθρα, δημοσιεύσεις και συνέδρια"]), bi("Initial enquiries should avoid confidential case details. No specialist legal certification is implied.", "Τα αρχικά αιτήματα δεν πρέπει να περιλαμβάνουν εμπιστευτικές λεπτομέρειες υποθέσεων. Δεν υπονοείται ειδική νομική πιστοποίηση.")),
        (bi("Logistics", "Logistics / Μεταφορές"), bi(["Corporate website, services and warehouse / fleet information", "Request-a-quote forms and lead management", "Custom quotation workflows and client portals where required"], ["Εταιρική ιστοσελίδα, υπηρεσίες και πληροφορίες αποθηκών / στόλου", "Φόρμες προσφορών και διαχείριση ενδιαφέροντος", "Προσαρμοσμένες ροές προσφορών και portals όπου απαιτούνται"]), bi("Designed around the information and operational steps your team actually needs.", "Σχεδιασμός βάσει των πληροφοριών και των λειτουργικών βημάτων που χρειάζεται η ομάδα σας.")),
        (bi("Accounting / Financial Services", "Λογιστικά / Οικονομικές υπηρεσίες"), bi(["Service presentation and appointment booking", "Lead qualification and automated email", "Articles, news and document / request workflows"], ["Παρουσίαση υπηρεσιών και κλείσιμο ραντεβού", "Διερεύνηση ενδιαφέροντος και αυτοματοποιημένα email", "Άρθρα, νέα και ροές εγγράφων / αιτημάτων"]), bi("Sensitive financial documents need a separately scoped, secure workflow.", "Ευαίσθητα οικονομικά έγγραφα απαιτούν ξεχωριστά σχεδιασμένη, ασφαλή ροή.")),
        (bi("Consulting / Professional Services", "Σύμβουλοι / Επαγγελματικές υπηρεσίες"), bi(["Services and appointment booking", "Business enquiry workflows and lead qualification", "Automated email, articles and request workflows"], ["Υπηρεσίες και προγραμματισμός ραντεβού", "Επιχειρηματικά αιτήματα και διερεύνηση αναγκών", "Αυτοματοποιημένα email, άρθρα και διαχείριση αιτημάτων"]), bi("Make it straightforward for the right prospects to take the next step.", "Διευκολύνετε τους ενδιαφερόμενους να κάνουν το επόμενο βήμα.")),
    ],
    "process": [
        (bi("Discovery", "Διερεύνηση"), bi("A short call about your business, requirements and priorities.", "Μια σύντομη συζήτηση για την επιχείρηση, τις ανάγκες και τις προτεραιότητες.")),
        (bi("Planning", "Σχεδιασμός"), bi("Agree the scope, structure, integrations, timeline and written quote.", "Συμφωνία για εύρος, δομή, διασυνδέσεις, χρονοδιάγραμμα και γραπτή προσφορά.")),
        (bi("Development", "Ανάπτυξη"), bi("Build the interface and workflows, with room for agreed feedback.", "Ανάπτυξη διεπαφής και ροών, με χώρο για τη συμφωνημένη ανατροφοδότηση.")),
        (bi("Testing", "Δοκιμές"), bi("Check forms, integrations, responsive layouts and the main customer paths.", "Έλεγχος φορμών, διασυνδέσεων, responsive εμφάνισης και βασικών διαδρομών πελάτη.")),
        (bi("Launch", "Ανάρτηση"), bi("Prepare production configuration, deployment and a practical handover.", "Προετοιμασία ρυθμίσεων production, deployment και πρακτική παράδοση.")),
        (bi("Maintenance", "Συντήρηση"), bi("Keep the agreed system supported; quote substantial changes separately.", "Υποστήριξη του συμφωνημένου συστήματος· ξεχωριστή κοστολόγηση σημαντικών αλλαγών.")),
    ],
}

CHOICES = {
    "industry": [("healthcare", bi("Healthcare", "Υγεία")), ("legal", bi("Legal", "Νομικά")), ("logistics", bi("Logistics", "Logistics")), ("finance", bi("Accounting / Finance", "Λογιστικά / Οικονομικά")), ("consulting", bi("Consulting", "Συμβουλευτική")), ("other", bi("Other", "Άλλο"))],
    "requirements": [("website", bi("New website", "Νέα ιστοσελίδα")), ("redesign", bi("Website redesign", "Ανασχεδιασμός ιστοσελίδας")), ("booking", bi("Booking system", "Σύστημα booking")), ("intake", bi("Client intake / forms", "Φόρμες πελατών")), ("automation", bi("Business automation", "Αυτοματισμοί επιχειρήσεων")), ("payments", bi("Payment system", "Σύστημα πληρωμών")), ("dashboard", bi("Admin dashboard", "Πίνακας διαχείρισης")), ("app", bi("Custom web application", "Custom web εφαρμογή")), ("unsure", bi("Not sure yet", "Δεν είμαι σίγουρος/η ακόμη"))],
    "budget": [("under1000", bi("Under €1,000", "Κάτω από €1,000")), ("1000-2000", bi("€1,000–€2,000", "€1,000–€2,000")), ("2000-3500", bi("€2,000–€3,500", "€2,000–€3,500")), ("3500-5000", bi("€3,500–€5,000", "€3,500–€5,000")), ("5000+", bi("€5,000+", "€5,000+")), ("unsure", bi("Not sure yet", "Δεν είμαι σίγουρος/η ακόμη"))],
    "timeframe": [("asap", bi("As soon as possible", "Το συντομότερο δυνατό")), ("month", bi("Within 1 month", "Εντός 1 μήνα")), ("quarter", bi("1–3 months", "1–3 μήνες")), ("flexible", bi("Flexible", "Ευέλικτο"))],
}

# Page-specific descriptions are reused for social metadata.
META = {
    "home": bi("Professional website development, custom web applications and business automation by Vasilis Xentes. Explore packages and book a consultation.", "Κατασκευή ιστοσελίδων, web εφαρμογές και αυτοματισμοί επιχειρήσεων από τον Βασίλη Ξεντέ. Δείτε πακέτα και κλείστε μια συζήτηση."),
    "services": bi("Professional websites, booking systems, business automation and Flask web applications tailored to your business.", "Επαγγελματικές ιστοσελίδες, online booking, αυτοματισμοί και custom web development για την επιχείρησή σας."),
    "industries": bi("Website and workflow solutions for medical practices, law firms, logistics, accounting and professional services.", "Ιστοσελίδες και ροές εργασίας για ιατρεία, δικηγορικά γραφεία, logistics, λογιστές και επαγγελματίες."),
    "portfolio": bi("Explore an anonymized technical case study of booking, client intake, admin workflows and payment integration capabilities.", "Ανώνυμη τεχνική παρουσίαση δυνατοτήτων booking, φορμών πελατών, διαχείρισης και πληρωμών."),
    "pricing": bi("Website packages from €980, business automation from €1,700 and custom systems from €3,000. Clear maintenance options.", "Πακέτα ιστοσελίδων από €980, αυτοματισμοί από €1,700 και custom συστήματα από €3,000. Ξεκάθαρες επιλογές συντήρησης."),
    "process": bi("From discovery and planning to development, testing, launch and maintenance: how a project comes together.", "Από τη διερεύνηση και τον σχεδιασμό στην ανάπτυξη, τις δοκιμές, την ανάρτηση και τη συντήρηση."),
    "about": bi("Meet Vasilis Xentes: an Applied Informatics background and a practical focus on web development and business automation.", "Γνωρίστε τον Βασίλη Ξεντέ: υπόβαθρο Εφαρμοσμένης Πληροφορικής και έμφαση στην ανάπτυξη web και τους αυτοματισμούς."),
    "contact": bi("Share your project requirements with Vasilis Xentes, email directly or arrange a discovery call.", "Μοιραστείτε τις ανάγκες του έργου με τον Βασίλη Ξεντέ, στείλτε email ή κλείστε μια συζήτηση."),
    "book-call": bi("Book a short discovery call to discuss your website or automation project with Vasilis Xentes.", "Κλείστε μια σύντομη συζήτηση με τον Βασίλη Ξεντέ για την ιστοσελίδα ή τον αυτοματισμό σας."),
    "privacy": bi("How this website handles enquiry details, email notifications and optional Calendly bookings. Draft for launch review.", "Πώς διαχειρίζεται η ιστοσελίδα στοιχεία αιτημάτων, email και προαιρετικό Calendly booking. Προσχέδιο προς έλεγχο."),
    "terms": bi("Website use, project scope, pricing and third-party services. Draft terms for review before launch.", "Χρήση ιστοσελίδας, εύρος έργου, τιμές και υπηρεσίες τρίτων. Προσχέδιο όρων προς έλεγχο πριν την ανάρτηση."),
}
