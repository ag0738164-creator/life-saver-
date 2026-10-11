from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import DonationRecord, DonationCamp, BloodInventory, EmergencyAlert
from app.routes import donor_required

donor_bp = Blueprint('donor', __name__)

@donor_bp.before_request
@login_required
@donor_required
def donor_guard():
    pass


@donor_bp.route('/dashboard')
def dashboard():
    profile = current_user.donor_profile
    donations = current_user.donations.order_by(DonationRecord.donation_date.desc()).all()
    total_donated_units = sum(d.units_donated for d in donations if d.status == 'Completed')
    lives_saved = total_donated_units * 3

    # Upcoming camps in user's city or nearest
    upcoming_camps = DonationCamp.query.filter(
        DonationCamp.camp_date >= date.today()
    ).order_by(DonationCamp.camp_date.asc()).limit(4).all()

    # Stock of user's blood group
    user_stock = BloodInventory.query.filter_by(blood_group=profile.blood_group).first() if profile else None

    # Emergency Alerts targeting this donor
    emergency_alerts = current_user.emergency_alerts.order_by(EmergencyAlert.sent_at.desc()).limit(3).all()

    return render_template(
        'donor/dashboard.html',
        profile=profile,
        donations=donations[:5],
        total_donated_units=total_donated_units,
        lives_saved=lives_saved,
        upcoming_camps=upcoming_camps,
        user_stock=user_stock,
        emergency_alerts=emergency_alerts
    )


@donor_bp.route('/donate', methods=['GET', 'POST'])
def donate():
    profile = current_user.donor_profile
    upcoming_camps = DonationCamp.query.filter(
        DonationCamp.camp_date >= date.today()
    ).order_by(DonationCamp.camp_date.asc()).all()

    if request.method == 'POST':
        camp_id = request.form.get('camp_id') or None
        donation_date_str = request.form.get('donation_date')
        notes = request.form.get('notes', '').strip()

        if not profile.is_eligible:
            flash(
                f'According to our records, you will be eligible for donation on {profile.next_eligible_date.strftime("%b %d, %Y")}.',
                'warning'
            )
            return redirect(url_for('donor.donate'))

        donation_date = date.today()
        if donation_date_str:
            try:
                donation_date = datetime.strptime(donation_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        # Create scheduled donation record
        donation = DonationRecord(
            donor_id=current_user.id,
            camp_id=camp_id,
            blood_group=profile.blood_group,
            units_donated=1,
            donation_date=donation_date,
            status='Scheduled',
            notes=notes or 'Self-scheduled donation appointment'
        )
        db.session.add(donation)
        db.session.commit()

        flash(
            f'Your donation appointment has been successfully scheduled for {donation_date.strftime("%b %d, %Y")}! Our team looks forward to seeing you.',
            'success'
        )
        return redirect(url_for('donor.history'))

    return render_template('donor/donate.html', profile=profile, upcoming_camps=upcoming_camps)


@donor_bp.route('/history')
def history():
    donations = current_user.donations.order_by(DonationRecord.donation_date.desc()).all()
    return render_template('donor/history.html', donations=donations)


@donor_bp.route('/card')
def donor_card():
    profile = current_user.donor_profile
    total_donations = current_user.donations.filter_by(status='Completed').count()
    return render_template('donor/donor_card.html', profile=profile, total_donations=total_donations)


@donor_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    profile = current_user.donor_profile
    if request.method == 'POST':
        current_user.name = request.form.get('name', '').strip() or current_user.name
        current_user.phone = request.form.get('phone', '').strip()
        current_user.city = request.form.get('city', '').strip()
        current_user.address = request.form.get('address', '').strip()

        age = request.form.get('age', type=int)
        weight = request.form.get('weight', type=float)
        medical_notes = request.form.get('medical_notes', '').strip()

        if profile:
            if age:
                profile.age = age
            if weight:
                profile.weight = weight
            profile.medical_notes = medical_notes

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('donor.dashboard'))

    return render_template('donor/profile.html', profile=profile)
