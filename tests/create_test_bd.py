import sqlite3

conn = sqlite3.connect("sqlite.db")
cursor = conn.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS emails (
        id INTEGER PRIMARY KEY,
        company TEXT,
        email TEXT,
        topic TEXT
    )
"""
)

data_to_insert = [
    (1, "SecureNet Solutions", "security@securenet.example", "cybersecurity"),
    (2, "DataVision Analytics", "analytics@datavision.example", "data_ai"),
    (3, "InfraCore Systems", "infra@infracore.example", "infrastructure"),
    (4, "DevSoft Engineering", "backend@devsoft.example", "programming"),
    (5, "CyberWall Group", "admin@cyberwall.example", "cybersecurity"),
    (6, "BigData Processing", "info@bigdata.example", "data_ai"),
    (7, "Network Enterprise", "support@netenterprise.example", "infrastructure"),
    (8, "Python Solutions", "dev@pythonsolutions.example", "programming"),
    (9, "SOC Monitoring Center", "soc@socmonitor.example", "cybersecurity"),
    (10, "AI Analytics Lab", "ai@analyticslab.example", "data_ai"),
    (11, "DataCenter Systems", "dc@datacenter.example", "infrastructure"),
    (12, "API Development Team", "api@apidev.example", "programming"),
]

cursor.executemany(
    """
    INSERT OR IGNORE INTO emails (id, company, email, topic)
    VALUES (?, ?, ?, ?)
""",
    data_to_insert,
)

conn.commit()
conn.close()

print("Данные успешно сохранены!")
