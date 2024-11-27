# DANCEshare
#### <URL https:>
#### DANCEshare is a web platform designed for sharing and discovering dance choreography. It allows users to upload and watch dance videos, connect with other dancers, and build a community united by their passion for dance. Inspires creativity and brings dancers together from all over the world.
### File Structure
- __data__ : in it is located database (danceshare.db).
- __static__ : in if are .js scripts and main style.
    - __ico__ : photos for nav. bar.
- __temp_uploads__ : as name sudjests is vrere video files are saved for converting filetype or jost checking filesize.
- __templates__ : where are html templates are stored.
- __app.py__ : is the main file, contains all the logic of the web application _more info later in readme_.
- __helpers.py__ : contains finction for checking if file type is allowed and login required.
- __video_helper.py__ : contains finction for creating picture from video, checking video size, checking video length and deleting video and picture.
- __tomp4.py__ : contains finction for converting video to mp4 and function to get video size.
- __requirements.txt__ : contains all the dependencies for the web application.

### All about links
- __/__ (POST, GET) : is the main page of the web application, it contains all the videos uploaded by users and a search bar to find videos by name or group.
- __/search__ (GET) **API** :  returns all the videos that match the search query.
- __/delete-account/[user_id]__ (POST) **API** : deletes the account.
- __/logout__ (GET) : logs out the user.
- __/login__ :
    - (POST) **API** : checks if the user is valid and logs in the user.
    - (GET) : shows the login page.
- __/register__ :
    - (POST) **API** : checks if the user isn't already registered and registers the user.
    - (GET) : shows the register page.
- __/upload__ :
    - (POST) **API** : saves video to the database, converts video to mp4 and creates picture from video.
    - (GET) : shows the upload page.
- __/options__ (GET) : shows the options page.
- __/create-group__ :
    - (POST) **API** : creates group in the database.
    - (GET) : shows the create group page.
- __/video/[video_id]/edit__ :
    - (POST) **API** : edits video in the database (name and description).
    - (GET) : shows the edit video page.
- __/video/[video_id]/delete__ (POST) **API** : deletes video from the database if user is owner or creator of group in which video is.
- __/group/[group_id]/edit__ :
    - (POST) **API** : edits group in the database (name, description, password and public status).
    - (GET) : shows the edit group page with group info.
- __/browse-groups__ (GET) : shows the browse groups page.
- __/browse-qroups-api__ (GET) **API**: returns all the groups that match the search query.
- __/group/[group_id]/join__ **API** : If user is not in group adds user to group. Checks if group is password protected and redirects to password page (/group/[group_id]/join/password) if it is.
- __/group/[group_id]/join/password__ :
    - (POST) **API** : checks if password is correct and adds user to group.
    - (GET) : shows the password page. 
- __/group/[group_id]/leave__ (GET) **API** : removes user from group.
- __/group/[group_id]/delete__ (POST) **API** : deletes group from the database and all the videos in it.
- __page not found__ 404: shows the page not found page.

#### Docker:
```
docker pull cekluka/danceshare:1.01
```

#### [GitHub](https://github.com/LukaCek/danceshare).


#### Help:
Error massages on /upload page are not working and I have no idea why.
if you want to try to fix it, please let me know.