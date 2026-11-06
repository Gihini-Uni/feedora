# Feedora

Feedora is a gamified web-based survey platform for measuring hedonic system adoption using the Hedonic-Motivation System Adoption Model (HMSAM).

**Live site:** https://gihiniw.pythonanywhere.com/

## Tech stack

- **Backend:** Django (Python)
- **Frontend:** Bootstrap 5, vanilla JavaScript
- **Database:** SQLite
- **Charts:** Chart.js
- **Hosting:** PythonAnywhere

## User roles

- **Survey creators** build surveys, enable gamification features, publish them and view results.
- **Respondents** complete surveys and earn points, experience (XP), levels and badges.

---

## Installation guide

Feedora runs locally with Python and a virtual environment. No separate database server is needed because it uses SQLite.

### Requirements

| Component | Requirement |
| --- | --- |
| Python | [version, e.g. 3.10 or later] |
| Package manager | pip |
| Version control | Git |
| Browser | Any modern browser (Chrome, Edge, Firefox) |

### Local installation

1. Clone the repository and open the project folder:

   ```bash
   git clone [repository URL]
   cd feedora
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # macOS/Linux
   ```

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Configure the settings in `settings.py` (or a `.env` file): `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and the SMTP email settings (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`) if email features are used.

5. Create the database tables:

   ```bash
   python manage.py migrate
   ```

6. Create an administrator account:

   ```bash
   python manage.py createsuperuser
   ```

7. Start the development server:

   ```bash
   python manage.py runserver
   ```

   Then open http://127.0.0.1:8000/ in your browser.

### Deployment on PythonAnywhere

1. Open a Bash console on PythonAnywhere, clone the repository, then create a virtual environment and install the dependencies (steps 1 to 3 above).
2. On the **Web** tab, add a new web app using **Manual configuration** with the matching Python version, and set the virtual environment path.
3. Edit the WSGI configuration file so it points to the project folder and its settings module.
4. Set `DEBUG = False` and add the PythonAnywhere domain to `ALLOWED_HOSTS`.
5. Run `python manage.py collectstatic`, then add a static files mapping from `/static/` to the `STATIC_ROOT` folder.
6. Run `python manage.py migrate`, then click **Reload** on the Web tab.

---

## User manual

### Survey creators

1. **Register or log in.** Create a creator account, or log in with an existing one. You are taken to the creator dashboard.
2. **Create a survey.** Select the option to create a new survey and enter its title and description.
3. **Add questions.** Use the survey builder to add questions and choose a question type, such as multiple choice or [other question types available]. Add the answer options for each question.
4. **Add gamification features.** Open **Add Features** to enable points, XP, levels and badges. Leave them disabled to publish a plain (non-gamified) survey.
5. **Publish and share.** Publish the survey and share its link with respondents.
6. **Edit a published survey.** Open the survey, make changes and re-publish. Existing answer options are kept, so earlier responses remain linked to them.
7. **View results.** Open the dashboard to see responses summarised in charts.
8. **Manage your profile.** Open the creator profile page to see your surveys and account details.

### Respondents

1. **Open the survey.** Click the link shared by the survey creator. [Log in or register if required.]
2. **Answer the questions.** Respond to each question and move through the survey.
3. **Earn rewards.** In gamified surveys, you earn points and XP as you answer, level up and unlock badges.
4. **Submit.** Submit the survey when all required questions are answered. A confirmation is shown once your response is saved.
5. **View your profile.** Open the respondent profile page to see your points, level and badges.

---

## Troubleshooting

| Problem | Solution |
| --- | --- |
| Changes do not appear after an update | Hard refresh the browser (Ctrl + Shift + R) to clear cached files. |
| Pages load without styling | Run `python manage.py collectstatic` and check the static files mapping. |
| Database or migration errors | Run `python manage.py makemigrations`, then `python manage.py migrate`. |
| Server error on PythonAnywhere | Check the error log on the Web tab, fix the issue, then click **Reload**. |
| Emails are not sent | Check the SMTP settings and use an app password if your email provider requires one. |
