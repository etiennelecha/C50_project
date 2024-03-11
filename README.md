# Pottery class #101
### Video démo: https://youtu.be/UpBeSxwfGmg
### Description
### General considerations and purpose

**The project is a web-based application, using python (and Flask) to manage the backend part of the site**. As a way for teachers to manage students and classes, not only pottery ones, and for students to book their sessions, it mostly consits in a variety of forms collecting user input that will then make their way into a general database.

The main user interaction is through a calendar dispaying available sessions. Via context items, and depending on who you are, you can then act on those sessions in different ways: adding, updating and deleting for the teacher (which we will call ***admin*** later), or just booking and see your next sessions for a normal user.

There are two main ways to access the site: as an **admin**, ie as someone **unique** whose username is `admin` (the site asks for first and last name, but those are irrelevant here), or as a **user** with no particular privileges. Different pages will be displayed to those to profiles.

### Contents of the ~/project folder

#### HTML templates, static folder

There 7 HTML templates used to display the pages. All expand on `layout.html`, which is profile sensitive to display the correct available tabs depending on the profile of users.

We also use additional javascript and CSS files to allow the use of a time picker (`jquery.datetimepicker.min.js/css`) and of the calendar interface (`js-year-calendar.min.js/css`). This interface is meant to be user-friendly, allowing on-day clicking to book or create a session, as well as contextual events trigerring modal pop-up to interact in a more granular way with the sessions, as seen in `index.html` and `dashboard.html`.

##### Database structure

The database consists is relationnal and consists in **two primary tables** called `users` and `classes`. We tried to keep the structure for each of those as simple as possible, storing data relevant for this project only. 
The relational table is called `bookings`, and stores only two additional data field: a time stamp `booking_time` and `class_attended`, which is a boolean checking for students' actual attendance, useful for managing the remaining classes a student have.

#### `App.py` and `helpers.py`

`App.py` make use of two decorators to distinguish between student and admin. Additionally, to allow proper tab display from the `layout.html` page, we store the admin database ID `ADMIN_ID` as a global variable and pass it via jinja and the `render_template` function.

Aside from the classical database management throuhg sqlite, which is natively supported, we use so called **"constructor functions"** that takes the SQLite primary tables and return a jsonify object that can then be fed to the javascript code, which handles communication between the two neatly. It is then very easy to make use of SQL content via javascript code. Those functions also take additional arguments which are used to filter relevant content.

`Helpers.py` defines the decorator functions, as long error pages.

### Admin route

The **"Admin route"** is called when someone with the username *admin* logs in. **Prior to the registraton of the admin, this route is not available at all**.

#### Dashboard page

This page display a calendar with all the classes, past and future. Clicking or right-clicking on one of them trigger events, wich are handled though modals: ***creating an event***, where you can optionnally specify max attendance and time after left-clicking on a date in the calender, ***updating an event***, which is accessible after right clicking on an existing event and covers the same functions, and ***deleting an event***, also accessible through right-clicking. You can also see a "***list of attendees***" for your sessions. If this is a past session, you will be able to confirm (or not) the actual attendance of any studend who booked.

#### See_users page

This page is a table when you can search by name, it uses dynamic updating through callback, features a button to update the number of sessions availble to each student, useful in the context of a per session payment and a display of the remainig sessions available to each student.

### User route

This is the route any user who is not the *admin* sees. It consists of only one page, `index.html`. Here you see the same calendar as in `dashboard.html`, but **with only future sessions**, which you will be able to book. It also contains a recap of your booked sessions in the upcoming three months.
