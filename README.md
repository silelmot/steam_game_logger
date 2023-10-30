
# Steam Game Logging

The main goal of this script is to log the playtime of all Steam games. Here are the key events and data that the script stores in the database:

## Features

1. **User Information:**
    - The script captures the name of the user and assigns them a unique user ID.
    - This information is stored in the `Users` table.

2. **Game Information:**
    - The script captures the name of the game and its Steam AppId.
    - This information is stored in the `Games` table.

3. **Game Sessions:**
    - When a game starts, a new game session is created in the database.
    - The `GameSessions` table stores the user ID, game ID, start time of the session, and duration of the session.

4. **Age Restrictions:**
    - The script checks the age restriction of the user and the game.
    - If the user is not old enough to play the game, the session is terminated immediately, and the corresponding message is logged.

5. **Logging:**
    - All significant events, such as starting a game, ending a game, adding or removing users or games, and checking age restrictions, are recorded in a log file.

All this information helps to create a detailed record of game duration and user gaming behavior, which can be used for various purposes, such as seeing which games are most popular, how long users play on average, or to ensure that users only play age-appropriate games.

## Future Enhancements

1. **Remote Control and Lifting Restrictions:**
    - The script will include features for remote control and lifting game restrictions.

2. **Dashboard for Administration:**
    - A dashboard will be created for easy administration of users, games, and restrictions.

3. **Detecting Running but Unplayed Games:**
    - The script will detect games that are running but not being played and terminate them to save resources.

4. **Installation Script:**
    - A streamlined installation process to make the setup of the logging system easier.

5. **Automatic Game Detection and Integration:**
    - Enhancing the script's capability to automatically detect and integrate new games (note: basic functionality is already present).

6. **Statistics Page:**
    - An associated statistics page will be developed to provide in-depth evaluations and insights based on the logged data.

