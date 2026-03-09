# אנחנו נייצר קובץ של 50,000 בתים (50KB)
# זה שווה ל-100 חבילות של 500 בתים, מספיק כדי לראות את האלגוריתם עובד קשה
fake_data = b"V" * 50000

with open("video_720p.mp4", "wb") as video_file:
    video_file.write(fake_data)

print("Fake video created successfully!")