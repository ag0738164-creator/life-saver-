from datetime import date
from flask import Blueprint, render_template, request
from app.models import BloodInventory, DonationCamp, User, DonationRecord, BloodRequest

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Live stock summary
    inventory = BloodInventory.query.order_by(BloodInventory.blood_group).all()
    total_units = sum(item.units_available for item in inventory)
    
    # Platform metrics
    total_donors = User.query.filter_by(role='donor').count()
    total_hospitals = User.query.filter_by(role='hospital').count()
    total_donations = DonationRecord.query.filter_by(status='Completed').count()
    fulfilled_requests = BloodRequest.query.filter_by(status='Dispensed').count()

    # Upcoming camps (up to 3 for homepage)
    upcoming_camps = DonationCamp.query.filter(
        DonationCamp.camp_date >= date.today()
    ).order_by(DonationCamp.camp_date.asc()).limit(3).all()

    return render_template(
        'index.html',
        inventory=inventory,
        total_units=total_units,
        total_donors=total_donors,
        total_hospitals=total_hospitals,
        total_donations=total_donations,
        fulfilled_requests=fulfilled_requests,
        upcoming_camps=upcoming_camps
    )

@main_bp.route('/stock')
def stock():
    search_group = request.args.get('blood_group', '').strip().upper()
    query = BloodInventory.query
    if search_group:
        query = query.filter_by(blood_group=search_group)
    inventory = query.order_by(BloodInventory.blood_group).all()
    total_units = sum(item.units_available for item in inventory)

    return render_template('stock.html', inventory=inventory, total_units=total_units, selected_group=search_group)

@main_bp.route('/eligibility')
def eligibility():
    return render_template('eligibility.html')

@main_bp.route('/camps')
def camps():
    search_city = request.args.get('city', '').strip()
    query = DonationCamp.query.filter(DonationCamp.camp_date >= date.today())
    if search_city:
        query = query.filter(DonationCamp.city.ilike(f'%{search_city}%'))
    camps = query.order_by(DonationCamp.camp_date.asc()).all()

    return render_template('camps.html', camps=camps, search_city=search_city)
