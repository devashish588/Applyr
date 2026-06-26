from email_module.sender import EmailSender

sender = EmailSender()

print("Configured:", sender.configured)

result = sender.send_test("bosedevashish7@gmail.com")

print(result)