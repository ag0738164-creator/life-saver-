from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, DonorProfile, HospitalProfile

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_donor:
            return redirect(url_for('donor.dashboard'))
        elif current_user.is_hospital:
            return redirect(url_for('hospital.dashboard'))
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not email or not password:
            flash('Please provide both email and password.', 'danger')
            return render_template('auth/login.html')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact the administrator.', 'danger')
                return render_template('auth/login.html')

            login_user(user, remember=remember)
            flash(f'Welcome back, {user.name}!', 'success')

            # Redirect to next URL if safe, otherwise to role dashboard
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)

            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            elif user.is_donor:
                return redirect(url_for('donor.dashboard'))
            elif user.is_hospital:
                return redirect(url_for('hospital.dashboard'))
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/register/donor', methods=['GET', 'POST'])
def register_donor():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        city = request.form.get('city', '').strip()
        address = request.form.get('address', '').strip()
        blood_group = request.form.get('blood_group', '').strip().upper()
        gender = request.form.get('gender', '')
        age_str = request.form.get('age', '').strip()
        weight_str = request.form.get('weight', '').strip()
        last_donation_str = request.form.get('last_donation_date', '').strip()
        medical_notes = request.form.get('medical_notes', '').strip()

        # Validation
        if not name or not email or not password or not blood_group:
            flash('Name, email, password, and blood group are required fields.', 'danger')
            return render_template('auth/register_donor.html')

        if password != confirm_password:
            flash('Passwords do not match. Please re-enter.', 'danger')
            return render_template('auth/register_donor.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register_donor.html')

        if User.query.filter_by(email=email).first():
            flash('An account with this email address already exists. Please log in.', 'warning')
            return redirect(url_for('auth.login'))

        age = int(age_str) if age_str.isdigit() else None
        weight = float(weight_str) if weight_str else None
        last_donation_date = None
        if last_donation_str:
            try:
                last_donation_date = datetime.strptime(last_donation_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        try:
            # Create user
            new_user = User(
                name=name,
                email=email,
                role='donor',
                phone=phone,
                city=city,
                address=address
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.flush()

            # Create donor profile
            donor_prof = DonorProfile(
                user_id=new_user.id,
                blood_group=blood_group,
                gender=gender,
                age=age,
                weight=weight,
                last_donation_date=last_donation_date,
                medical_notes=medical_notes
            )
            db.session.add(donor_prof)
            db.session.commit()

            flash('Registration successful! Please log in with your credentials.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred during registration: {str(e)}', 'danger')

    return render_template('auth/register_donor.html')


@auth_bp.route('/register/hospital', methods=['GET', 'POST'])
def register_hospital():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        city = request.form.get('city', '').strip()
        address = request.form.get('address', '').strip()
        license_number = request.form.get('license_number', '').strip()
        hospital_type = request.form.get('hospital_type', 'General').strip()
        emergency_contact = request.form.get('emergency_contact', '').strip()

        # Validation
        if not name or not email or not password or not license_number:
            flash('Hospital name, email, password, and license number are required.', 'danger')
            return render_template('auth/register_hospital.html')

        if password != confirm_password:
            flash('Passwords do not match. Please re-enter.', 'danger')
            return render_template('auth/register_hospital.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register_hospital.html')

        if User.query.filter_by(email=email).first():
            flash('An account with this email address already exists. Please log in.', 'warning')
            return redirect(url_for('auth.login'))

        try:
            # Create user
            new_user = User(
                name=name,
                email=email,
                role='hospital',
                phone=phone,
                city=city,
                address=address
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.flush()

            # Create hospital profile
            hosp_prof = HospitalProfile(
                user_id=new_user.id,
                license_number=license_number,
                hospital_type=hospital_type,
                emergency_contact=emergency_contact,
                is_verified=True
            )
            db.session.add(hosp_prof)
            db.session.commit()

            flash('Hospital registered successfully! You can now log in to raise blood requests.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred during hospital registration: {str(e)}', 'danger')

    return render_template('auth/register_hospital.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been successfully logged out.', 'info')
    return redirect(url_for('main.index'))
