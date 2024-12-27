import asyncio
from telethon.sync import TelegramClient
from telethon import errors

class main:
    def __init__(self, api_id, api_hash, phone_number):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.client = TelegramClient('session_' + phone_number, api_id, api_hash)
        self.lock = asyncio.Lock()  # Lock to handle concurrency

    async def connect_client(self):
        await self.client.connect()
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            try:
                await self.client.sign_in(self.phone_number, input('Enter the code: '))
            except errors.rpcerrorlist.SessionPasswordNeededError:
                password = input('Two-step verification is enabled. Enter your password: ')
                await self.client.sign_in(password=password)

    async def list_chats(self):
        await self.connect_client()
        dialogs = await self.client.get_dialogs()

        with open(f"chats_of_{self.phone_number}.txt", "w", encoding="utf-8") as chats_file:
            for dialog in dialogs:
                chat_info = f"Chat ID: {dialog.id}, Title: {dialog.title or '[No Title]'}"
                print(chat_info)
                chats_file.write(chat_info + "\n")
        print("List of groups printed successfully!")

    async def forward_messages_from_sources(self, source_chat_ids, destination_channel_id, keywords):
        await self.connect_client()
        destination_channel = await self.client.get_entity(destination_channel_id)

        # Create tasks for each source channel
        tasks = [
            self.forward_messages_to_channel(source_chat_id, destination_channel, keywords)
            for source_chat_id in source_chat_ids
        ]
        await asyncio.gather(*tasks)  # Run all tasks concurrently

    async def forward_messages_to_channel(self, source_chat_id, destination_channel, keywords):
        last_message_id = (await self.client.get_messages(source_chat_id, limit=1))[0].id

        while True:
            async with self.lock:  # Prevent overlapping of forward operations
                messages = await self.client.get_messages(source_chat_id, min_id=last_message_id, limit=None)

                for message in reversed(messages):
                    if keywords:
                        if message.text and any(keyword.strip().lower() in message.text.lower() for keyword in keywords):
                            print(f"Message contains a keyword: {message.text}")
                            await self.forward_message(message, destination_channel)
                    else:
                        await self.forward_message(message, destination_channel)

                    last_message_id = max(last_message_id, message.id)

            await asyncio.sleep(5)  # Delay to avoid API rate limits

    async def forward_message(self, message, destination_channel):
        try:
            if message.media:
                await self.client.send_file(destination_channel, message.media, caption=message.text)
            else:
                await self.client.send_message(destination_channel, message.text)
            print(f"Message forwarded: {message.text or '[Media]'}")
        except Exception as e:
            print(f"Failed to forward message: {e}")

def read_credentials():
    try:
        with open("credentials.txt", "r") as file:
            lines = file.readlines()
            return lines[0].strip(), lines[1].strip(), lines[2].strip()
    except FileNotFoundError:
        return None, None, None

def write_credentials(api_id, api_hash, phone_number):
    with open("credentials.txt", "w") as file:
        file.write(api_id + "\n")
        file.write(api_hash + "\n")
        file.write(phone_number + "\n")

async def main():
    api_id, api_hash, phone_number = read_credentials()
    if not api_id or not api_hash or not phone_number:
        api_id = input("Enter your API ID: ")
        api_hash = input("Enter your API Hash: ")
        phone_number = input("Enter your phone number: ")
        write_credentials(api_id, api_hash, phone_number)

    forwarder = main(api_id, api_hash, phone_number)

    print("Choose an option:")
    print("1. List Chats")
    print("2. Forward Messages")

    choice = input("Enter your choice: ")
    if choice == "1":
        await forwarder.list_chats()
    elif choice == "2":
        source_chat_ids = [int(chat_id.strip()) for chat_id in input("Enter source chat IDs (comma-separated): ").split(",")]
        destination_channel_id = input("Enter the destination chat ID (can be a numeric ID or username): ")
        print("Enter keywords (comma-separated) or leave blank to forward all messages:")
        keywords = [keyword.strip() for keyword in input().split(",") if keyword.strip()]
        await forwarder.forward_messages_from_sources(source_chat_ids, destination_channel_id, keywords)
    else:
        print("Invalid choice")

if __name__ == "__main__":
    asyncio.run(main())
