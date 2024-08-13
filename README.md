# Discord-Member-Scraper-Selfbot
A simple discord server user/member scraper selfbot <br/>
Saves the list of ids to a json file.
## Features
- Choose between scraping current members or all users that have been in the server.
- Saves the list of user/member ids to a json file.
- Set the depth of how many messages per channel to scrape.
- Set a welcome channel to scrape bot's user-mentions for users at infinite message depth.
- Choose whether to stop within 150 users of the current member count. (Servers with <250 users are able to be scraped normally)
  - The script will ignore this if the server has less than 250 members.
## Running the Script
### Zip File
Download the zip file. <br/>
Extract the files. <br/>
Run /main.dist/main.exe
### via an IDE
This code will not work with vanilla discord.py, you need to install discord.py-self. <br/>
Run this command to install the latest discord.py-self branch: 
> pip install git+https://github.com/dolfies/discord.py-self@master#egg=discord.py-self
