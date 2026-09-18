from datetime import datetime, timezone
from database.database import db
from database.models import User, Candidate, Exam, Question, Setting
from auth.security import hash_password

def seed_default_data():
    """Seed default admin, manager, demo candidate, benchmark exams with questions, and settings."""
    
    # 1. Seed Settings
    default_settings = [
        ("face_absence_threshold_sec", "10.0", "Prolonged face absence threshold in seconds"),
        ("tab_switch_threshold", "3", "Max tab switches before flagging suspicious"),
        ("high_risk_tab_switch_threshold", "6", "High risk tab switch trigger"),
        ("window_blur_threshold", "3", "Max blur events before flagging"),
        ("monitoring_interval_ms", "1500", "Webcam ping interval in ms"),
        ("multiple_faces_threshold", "1", "Flag if >1 faces detected"),
        ("weight_face_absence", "10", "Risk points for face absence"),
        ("weight_tab_switch", "10", "Risk points per tab switch"),
        ("weight_focus_loss", "5", "Risk points per focus loss"),
        ("weight_multiple_faces", "30", "Risk points per multiple-face occurrence"),
        ("weight_fullscreen_exit", "10", "Risk points per fullscreen exit"),
        ("low_risk_min_score", "80.0", "Minimum score for LOW risk classification"),
        ("medium_risk_min_score", "50.0", "Minimum score for MEDIUM risk classification"),
    ]
    for key, val, desc in default_settings:
        if not Setting.query.filter_by(key=key).first():
            db.session.add(Setting(key=key, value=val, description=desc))

    # 2. Seed Users and linked Candidate records.
    accounts = [
        ("Prof. Marcus Sterling (Exam Manager)", "manager@examguard.com", "manager123", "manager"),
        ("Dr. Eleanor Vance (Chief Invigilator)", "admin@examguard.com", "admin123", "admin"),
        ("Alex Mercer", "candidate@examguard.com", "candidate123", "candidate"),
    ]
    for name, email, password, role in accounts:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(name=name, email=email, password_hash=hash_password(password), role=role)
            db.session.add(user)
            db.session.flush()
        else:
            user.role = role
        if role == "candidate" and not user.candidate:
            db.session.add(Candidate(user_id=user.id))
    db.session.commit()

    # 3. Seed Benchmark Exams
    if Exam.query.count() == 0:
        # Exam 1
        exam1 = Exam(
            title="CS401: Advanced Operating Systems & Systems Architecture",
            description="Comprehensive university examination covering virtual memory paging, process scheduling, synchronization primitives, and distributed filesystem consistency models.",
            duration_minutes=25,
            total_marks=50,
            passing_marks=25,
            status="active"
        )
        db.session.add(exam1)
        db.session.flush()

        questions_exam1 = [
            ("Which page replacement algorithm suffers from Belady's Anomaly?",
             "LRU (Least Recently Used)", "FIFO (First In First Out)", "Optimal Page Replacement", "Clock Algorithm", "B", 10),
            ("What is the primary function of the Translation Lookaside Buffer (TLB)?",
             "Cache virtual-to-physical address translations in hardware", "Execute atomic test-and-set instructions", "Coordinate DMA memory transfers", "Schedule I/O interrupt handlers", "A", 10),
            ("Which synchronization construct prevents Priority Inversion in real-time kernels?",
             "Peterson's Algorithm", "Priority Inheritance Protocol", "Spinlock with yield", "Semaphores without mutex locks", "B", 10),
            ("What does the copy-on-write (COW) technique optimize during fork() system calls?",
             "Immediate memory page replication", "Deferring physical page duplication until write occurs", "Instant thread termination", "Kernel stack allocation bypassing", "B", 10),
            ("Which of the following conditions is NOT required for a deadlock state to occur?",
             "Mutual Exclusion", "Hold and Wait", "Preemption of Allocated Resources", "Circular Wait", "C", 10)
        ]
        for q_text, a, b, c, d, correct, marks in questions_exam1:
            q = Question(
                exam_id=exam1.id,
                question_text=q_text,
                option_a=a,
                option_b=b,
                option_c=c,
                option_d=d,
                correct_option=correct,
                marks=marks
            )
            db.session.add(q)

        # Exam 2
        exam2 = Exam(
            title="DS302: Machine Learning & Statistical Inference",
            description="Midterm examination assessing supervised algorithms, regularization techniques, clustering heuristics, and probabilistic evaluation metrics.",
            duration_minutes=20,
            total_marks=50,
            passing_marks=25,
            status="active"
        )
        db.session.add(exam2)
        db.session.flush()

        questions_exam2 = [
            ("What is the primary effect of L1 regularization (Lasso) on model coefficients?",
             "Forces unimportant weights exactly to zero creating sparsity", "Smooths all weights uniformly without sparsity", "Maximizes variance of parameter estimates", "Inverts the covariance matrix", "A", 10),
            ("How does K-Means clustering initialize centroids in K-Means++?",
             "Purely uniform random selection across all space", "Selecting centers with probability proportional to squared distance from nearest existing center", "Assigning centers to the origin (0,0)", "Using principal eigenvector coordinates", "B", 10),
            ("Which metric is most appropriate for evaluating a highly imbalanced binary classifier?",
             "Raw Accuracy", "Precision-Recall AUC (PR-AUC) or F1-Score", "Mean Squared Error", "Explained Variance Ratio", "B", 10),
            ("In neural network backpropagation, what does the vanishing gradient problem primarily affect?",
             "Output softmax layers", "Early hidden layers in deep networks", "Feature scaling pipelines", "Hyperparameter grid search", "B", 10),
            ("What does the bias-variance tradeoff characterize in statistical learning?",
             "Underfitting due to high bias vs overfitting due to high variance", "Execution latency vs RAM footprint", "Batch size vs learning rate decay", "Number of trees vs maximum depth in random forests", "A", 10)
        ]
        for q_text, a, b, c, d, correct, marks in questions_exam2:
            q = Question(
                exam_id=exam2.id,
                question_text=q_text,
                option_a=a,
                option_b=b,
                option_c=c,
                option_d=d,
                correct_option=correct,
                marks=marks
            )
            db.session.add(q)

        # Exam 3
        exam3 = Exam(
            title="CYBER205: Network Security & Cryptographic Protocols",
            description="Assessment on public key infrastructure, TLS 1.3 handshakes, cipher modes, and common web application vulnerabilities.",
            duration_minutes=20,
            total_marks=40,
            passing_marks=20,
            status="active"
        )
        db.session.add(exam3)
        db.session.flush()

        questions_exam3 = [
            ("Which cryptographic property ensures past communications remain encrypted even if the private key is later compromised?",
             "Zero-Knowledge Proof", "Perfect Forward Secrecy (PFS)", "Homomorphic Encryption", "Message Authentication Code (MAC)", "B", 10),
            ("What type of attack does the Same-Origin Policy (SOP) in modern browsers primarily mitigate?",
             "Distributed Denial of Service (DDoS)", "Cross-Origin Unauthorized DOM and Resource Access", "SQL Injection in Server Backend", "Buffer Overflow in C Binaries", "B", 10),
            ("Which block cipher mode provides authenticated encryption with associated data (AEAD)?",
             "Electronic Codebook (ECB)", "Galois/Counter Mode (GCM)", "Cipher Block Chaining (CBC)", "Output Feedback (OFB)", "B", 10),
            ("In a TLS 1.3 handshake, which key exchange mechanism is strictly mandated?",
             "RSA static key exchange", "Ephemeral Diffie-Hellman (ECDHE / DHE)", "Plain unencrypted Diffie-Hellman", "Blowfish CBC exchange", "B", 10)
        ]
        for q_text, a, b, c, d, correct, marks in questions_exam3:
            q = Question(
                exam_id=exam3.id,
                question_text=q_text,
                option_a=a,
                option_b=b,
                option_c=c,
                option_d=d,
                correct_option=correct,
                marks=marks
            )
            db.session.add(q)

    db.session.commit()
