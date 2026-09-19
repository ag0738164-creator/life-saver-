import csv
import io
from datetime import datetime, date, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from app import db
from app.models import (
    BloodInventory, BloodRequest, DonationRecord, DonationCamp,
    User, DonorProfile, HospitalProfile, BloodBagUnit, EmergencyAlert
)
from app.services.ai_predictor import BloodDemandPredictor
from app.services.donor_matcher import EmergencyDonorMatcher
from app.services.qr_service import BloodUnitQRService
from app.routes import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
@login_required
@admin_required
def admin_guard():
    pass


@admin_bp.route('/dashboard')
def dashboard():
    inventory = BloodInventory.query.order_by(BloodInventory.blood_group).all()
    total_units = sum(item.units_available for item in inventory)
    critical_groups_count = sum(1 for item in inventory if item.is_critical)
    
    pending_requests_count = BloodRequest.query.filter_by(status='Pending').count()
    total_donors = User.query.filter_by(role='donor').count()
    total_hospitals = User.query.filter_by(role='hospital').count()
    completed_donations_count = DonationRecord.query.filter_by(status='Completed').count()

    # Recent pending and active requests
    recent_requests = BloodRequest.query.order_by(
        BloodRequest.created_at.desc()
    ).limit(6).all()

    # Recent completed donations
    recent_donations = DonationRecord.query.order_by(
        DonationRecord.created_at.desc()
    ).limit(6).all()

    # Chart data
    chart_labels = [item.blood_group for item in inventory]
    chart_data = [item.units_available for item in inventory]

    return render_template(
        'admin/dashboard.html',
        inventory=inventory,
        total_units=total_units,
        critical_groups_count=critical_groups_count,
        pending_requests_count=pending_requests_count,
        total_donors=total_donors,
        total_hospitals=total_hospitals,
        completed_donations_count=completed_donations_count,
        recent_requests=recent_requests,
        recent_donations=recent_donations,
        chart_labels=chart_labels,
        chart_data=chart_data
    )


@admin_bp.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if request.method == 'POST':
        blood_group = request.form.get('blood_group', '').strip().upper()
        units_to_add = request.form.get('units', type=int)
        operation = request.form.get('operation', 'add')  # 'add', 'set', 'deduct'
        threshold = request.form.get('threshold', type=int)

        item = BloodInventory.query.filter_by(blood_group=blood_group).first()
        if not item:
            flash(f'Blood group {blood_group} not found.', 'danger')
            return redirect(url_for('admin.inventory'))

        if threshold is not None and threshold >= 0:
            item.critical_threshold = threshold

        if units_to_add is not None:
            if operation == 'add':
                item.units_available += units_to_add
                flash(f'Added {units_to_add} units to {blood_group}. Total: {item.units_available}', 'success')
            elif operation == 'deduct':
                if item.units_available < units_to_add:
                    flash(f'Cannot deduct {units_to_add} units. Only {item.units_available} units available.', 'danger')
                    return redirect(url_for('admin.inventory'))
                item.units_available -= units_to_add
                flash(f'Deducted {units_to_add} units from {blood_group}. Remaining: {item.units_available}', 'warning')
            elif operation == 'set':
                item.units_available = max(0, units_to_add)
                flash(f'Set {blood_group} inventory directly to {item.units_available} units.', 'info')

        item.last_updated = datetime.now(timezone.utc)
        db.session.commit()
        return redirect(url_for('admin.inventory'))

    inventory_list = BloodInventory.query.order_by(BloodInventory.blood_group).all()
    total_units = sum(i.units_available for i in inventory_list)
    return render_template('admin/inventory.html', inventory=inventory_list, total_units=total_units)


@admin_bp.route('/requests')
def requests_list():
    status_filter = request.args.get('status', 'All')
    query = BloodRequest.query
    if status_filter and status_filter != 'All':
        query = query.filter_by(status=status_filter)
    
    requests = query.order_by(
        # Sort Emergency first, then Critical, then Normal, and newest first
        BloodRequest.status == 'Pending',
        BloodRequest.created_at.desc()
    ).all()

    # Inventory lookup for quick availability checking in template
    inventory_map = {item.blood_group: item.units_available for item in BloodInventory.query.all()}

    return render_template(
        'admin/requests.html',
        requests=requests,
        status_filter=status_filter,
        inventory_map=inventory_map
    )


@admin_bp.route('/requests/<int:request_id>/approve', methods=['POST'])
def approve_request(request_id):
    req = BloodRequest.query.get_or_404(request_id)
    if req.status not in ('Pending', 'Rejected'):
        flash(f'Request #{req.id} is already {req.status}.', 'info')
        return redirect(url_for('admin.requests_list'))

    stock = BloodInventory.query.filter_by(blood_group=req.blood_group).first()
    if not stock or stock.units_available < req.units_requested:
        flash(
            f'Insufficient stock for {req.blood_group}! Needed: {req.units_requested}, Available: {stock.units_available if stock else 0}.',
            'danger'
        )
        return redirect(url_for('admin.requests_list'))

    admin_note = request.form.get('admin_notes', '').strip()
    
    # Decrement inventory
    stock.units_available -= req.units_requested
    stock.last_updated = datetime.now(timezone.utc)

    # Update request
    req.status = 'Approved'
    req.admin_notes = admin_note or 'Approved by blood bank administrator.'
    req.processed_at = datetime.now(timezone.utc)
    db.session.commit()

    flash(
        f'Request #{req.id} approved successfully! Deducted {req.units_requested} units of {req.blood_group}. Stock remaining: {stock.units_available}.',
        'success'
    )
    return redirect(url_for('admin.requests_list'))


@admin_bp.route('/requests/<int:request_id>/dispense', methods=['POST'])
def dispense_request(request_id):
    req = BloodRequest.query.get_or_404(request_id)
    if req.status != 'Approved':
        flash('Only approved requests can be marked as dispensed.', 'warning')
        return redirect(url_for('admin.requests_list'))

    req.status = 'Dispensed'
    db.session.commit()
    flash(f'Request #{req.id} marked as Dispensed to {req.hospital.name}.', 'success')
    return redirect(url_for('admin.requests_list'))


@admin_bp.route('/requests/<int:request_id>/reject', methods=['POST'])
def reject_request(request_id):
    req = BloodRequest.query.get_or_404(request_id)
    reason = request.form.get('admin_notes', 'Request rejected due to stock or operational constraints.')

    # If already approved, return units back to stock
    if req.status == 'Approved':
        stock = BloodInventory.query.filter_by(blood_group=req.blood_group).first()
        if stock:
            stock.units_available += req.units_requested
            stock.last_updated = datetime.now(timezone.utc)

    req.status = 'Rejected'
    req.admin_notes = reason
    req.processed_at = datetime.now(timezone.utc)
    db.session.commit()

    flash(f'Request #{req.id} has been rejected.', 'warning')
    return redirect(url_for('admin.requests_list'))


@admin_bp.route('/donations', methods=['GET', 'POST'])
def donations_list():
    if request.method == 'POST':
        donor_id = request.form.get('donor_id', type=int)
        camp_id = request.form.get('camp_id', type=int) or None
        units_donated = request.form.get('units_donated', type=int) or 1
        donation_date_str = request.form.get('donation_date')
        notes = request.form.get('notes', '').strip()

        donor = User.query.filter_by(id=donor_id, role='donor').first()
        if not donor or not donor.donor_profile:
            flash('Invalid donor selected.', 'danger')
            return redirect(url_for('admin.donations_list'))

        blood_group = donor.donor_profile.blood_group
        donation_date = date.today()
        if donation_date_str:
            try:
                donation_date = datetime.strptime(donation_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        # Create donation record
        record = DonationRecord(
            donor_id=donor.id,
            camp_id=camp_id,
            blood_group=blood_group,
            units_donated=units_donated,
            donation_date=donation_date,
            status='Completed',
            verified_by=current_user.name,
            notes=notes
        )
        db.session.add(record)

        # Increment inventory
        stock = BloodInventory.query.filter_by(blood_group=blood_group).first()
        if stock:
            stock.units_available += units_donated
            stock.last_updated = datetime.now(timezone.utc)

        # Update donor's last donation date
        donor.donor_profile.last_donation_date = donation_date
        db.session.commit()

        flash(
            f'Donation of {units_donated} unit(s) of {blood_group} successfully logged for {donor.name}! Inventory updated.',
            'success'
        )
        return redirect(url_for('admin.donations_list'))

    donations = DonationRecord.query.order_by(DonationRecord.donation_date.desc()).all()
    donors = User.query.filter_by(role='donor').order_by(User.name).all()
    camps = DonationCamp.query.order_by(DonationCamp.camp_date.desc()).all()

    return render_template('admin/donations.html', donations=donations, donors=donors, camps=camps)


@admin_bp.route('/donors')
def donors_list():
    blood_group_filter = request.args.get('blood_group', '').strip().upper()
    city_filter = request.args.get('city', '').strip()

    query = User.query.filter_by(role='donor')
    if city_filter:
        query = query.filter(User.city.ilike(f'%{city_filter}%'))
    
    donors = query.order_by(User.created_at.desc()).all()
    if blood_group_filter:
        donors = [d for d in donors if d.donor_profile and d.donor_profile.blood_group == blood_group_filter]

    return render_template(
        'admin/donors.html',
        donors=donors,
        blood_group_filter=blood_group_filter,
        city_filter=city_filter
    )


@admin_bp.route('/hospitals')
def hospitals_list():
    hospitals = User.query.filter_by(role='hospital').order_by(User.created_at.desc()).all()
    return render_template('admin/hospitals.html', hospitals=hospitals)


@admin_bp.route('/camps', methods=['GET', 'POST'])
def camps_management():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        organized_by = request.form.get('organized_by', '').strip()
        location = request.form.get('location', '').strip()
        city = request.form.get('city', '').strip()
        camp_date_str = request.form.get('camp_date', '').strip()
        start_time = request.form.get('start_time', '09:00 AM').strip()
        end_time = request.form.get('end_time', '05:00 PM').strip()
        contact_person = request.form.get('contact_person', '').strip()
        contact_phone = request.form.get('contact_phone', '').strip()
        description = request.form.get('description', '').strip()

        if not title or not organized_by or not location or not city or not camp_date_str:
            flash('All required camp details must be filled.', 'danger')
            return redirect(url_for('admin.camps_management'))

        try:
            camp_date = datetime.strptime(camp_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return redirect(url_for('admin.camps_management'))

        camp = DonationCamp(
            title=title,
            organized_by=organized_by,
            location=location,
            city=city,
            camp_date=camp_date,
            start_time=start_time,
            end_time=end_time,
            contact_person=contact_person,
            contact_phone=contact_phone,
            description=description,
            status='Upcoming'
        )
        db.session.add(camp)
        db.session.commit()
        flash(f'Donation Camp "{title}" scheduled successfully!', 'success')
        return redirect(url_for('admin.camps_management'))

    camps = DonationCamp.query.order_by(DonationCamp.camp_date.desc()).all()
    return render_template('admin/camps.html', camps=camps)


@admin_bp.route('/export/<data_type>')
def export_csv(data_type):
    output = io.StringIO()
    writer = csv.writer(output)

    if data_type == 'inventory':
        writer.writerow(['Blood Group', 'Units Available', 'Critical Threshold', 'Status', 'Last Updated'])
        for item in BloodInventory.query.order_by(BloodInventory.blood_group).all():
            writer.writerow([
                item.blood_group,
                item.units_available,
                item.critical_threshold,
                item.status_label,
                item.last_updated.strftime('%Y-%m-%d %H:%M:%S') if item.last_updated else ''
            ])
        filename = f'blood_inventory_{date.today()}.csv'

    elif data_type == 'requests':
        writer.writerow(['Request ID', 'Hospital Name', 'Blood Group', 'Units', 'Urgency', 'Patient Name', 'Status', 'Date'])
        for req in BloodRequest.query.order_by(BloodRequest.created_at.desc()).all():
            writer.writerow([
                req.id,
                req.hospital.name if req.hospital else 'N/A',
                req.blood_group,
                req.units_requested,
                req.urgency,
                req.patient_name,
                req.status,
                req.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        filename = f'blood_requests_{date.today()}.csv'

    elif data_type == 'donations':
        writer.writerow(['Donation ID', 'Donor Name', 'Blood Group', 'Units', 'Date', 'Status', 'Verified By'])
        for rec in DonationRecord.query.order_by(DonationRecord.donation_date.desc()).all():
            writer.writerow([
                rec.id,
                rec.donor.name if rec.donor else 'N/A',
                rec.blood_group,
                rec.units_donated,
                rec.donation_date.strftime('%Y-%m-%d'),
                rec.status,
                rec.verified_by or ''
            ])
        filename = f'donation_records_{date.today()}.csv'
    else:
        flash('Invalid export type.', 'danger')
        return redirect(url_for('admin.dashboard'))

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


# ---------------------------------------------------------
# Advanced Feature 1: AI-Based Blood Demand Prediction
# ---------------------------------------------------------
@admin_bp.route('/ai-predictions')
def ai_predictions():
    horizon = request.args.get('horizon', default=14, type=int)
    if horizon not in (7, 14, 30):
        horizon = 14

    forecast_results = BloodDemandPredictor.predict_demand(days_horizon=horizon)
    return render_template('admin/ai_predictions.html', forecast=forecast_results, horizon=horizon)


# ---------------------------------------------------------
# Advanced Feature 2: Location-Based Emergency Donor Matching
# ---------------------------------------------------------
@admin_bp.route('/emergency-match/<int:request_id>')
def emergency_match(request_id):
    req = BloodRequest.query.get_or_404(request_id)
    target_city = req.hospital.city if req.hospital else None

    matched_donors = EmergencyDonorMatcher.find_matching_donors(
        recipient_group=req.blood_group,
        target_city=target_city,
        max_results=20
    )

    compatible_groups = EmergencyDonorMatcher.get_compatible_donor_groups(req.blood_group)

    # Check already dispatched alerts for this request
    existing_alerts = EmergencyAlert.query.filter_by(request_id=req.id).all()
    alerted_donor_ids = {a.donor_id for a in existing_alerts}

    return render_template(
        'admin/emergency_match.html',
        req=req,
        matched_donors=matched_donors,
        compatible_groups=compatible_groups,
        existing_alerts=existing_alerts,
        alerted_donor_ids=alerted_donor_ids
    )


@admin_bp.route('/emergency-broadcast/<int:request_id>', methods=['POST'])
def emergency_broadcast(request_id):
    req = BloodRequest.query.get_or_404(request_id)
    selected_donor_ids = request.form.getlist('donor_ids', type=int)

    if not selected_donor_ids:
        flash('Please select at least one compatible donor to broadcast emergency alerts.', 'warning')
        return redirect(url_for('admin.emergency_match', request_id=request_id))

    dispatched = EmergencyDonorMatcher.dispatch_emergency_alerts(
        request_id=req.id,
        donor_ids=selected_donor_ids,
        hospital_name=req.hospital.name if req.hospital else "Emergency Hospital",
        blood_group=req.blood_group,
        units_needed=req.units_requested,
        urgency=req.urgency
    )

    flash(
        f'Emergency alert broadcast successfully sent via SMS and Email to {dispatched} nearby compatible donors!',
        'success'
    )
    return redirect(url_for('admin.emergency_match', request_id=request_id))


# ---------------------------------------------------------
# Advanced Feature 3: QR Code-Based Blood Unit Tracking
# ---------------------------------------------------------
@admin_bp.route('/qr-tracker')
def qr_tracker():
    status_filter = request.args.get('status', 'All')
    blood_group_filter = request.args.get('blood_group', '').strip().upper()

    query = BloodBagUnit.query
    if status_filter and status_filter != 'All':
        query = query.filter_by(status=status_filter)
    if blood_group_filter:
        query = query.filter_by(blood_group=blood_group_filter)

    units = query.order_by(BloodBagUnit.expiry_date.asc()).all()
    total_units_count = BloodBagUnit.query.count()
    in_storage_count = BloodBagUnit.query.filter_by(status='In Storage').count()
    expired_count = sum(1 for u in BloodBagUnit.query.all() if u.is_expired and u.status == 'In Storage')

    donors = User.query.filter_by(role='donor').order_by(User.name).all()

    return render_template(
        'admin/qr_tracker.html',
        units=units,
        status_filter=status_filter,
        blood_group_filter=blood_group_filter,
        total_units_count=total_units_count,
        in_storage_count=in_storage_count,
        expired_count=expired_count,
        donors=donors
    )


@admin_bp.route('/qr-scanner', methods=['GET', 'POST'])
def qr_scanner():
    scanned_unit = None
    search_query = request.args.get('unit_no', '').strip()

    if request.method == 'POST':
        search_query = request.form.get('barcode_input', '').strip()

    if search_query:
        # Search by exact unit_number or ID
        scanned_unit = BloodBagUnit.query.filter(
            (BloodBagUnit.unit_number.ilike(f'%{search_query}%'))
        ).first()

        if not scanned_unit:
            flash(f'No blood unit matching identifier "{search_query}" found in cold chain database.', 'danger')

    hospitals = User.query.filter_by(role='hospital').all()
    return render_template('admin/qr_scanner.html', unit=scanned_unit, search_query=search_query, hospitals=hospitals)


@admin_bp.route('/blood-unit/<int:unit_id>/label')
def unit_label(unit_id):
    unit = BloodBagUnit.query.get_or_404(unit_id)
    qr_image = unit.get_qr_image()
    return render_template('admin/unit_label.html', unit=unit, qr_image=qr_image)


@admin_bp.route('/blood-unit/<int:unit_id>/status', methods=['POST'])
def update_unit_status(unit_id):
    unit = BloodBagUnit.query.get_or_404(unit_id)
    new_status = request.form.get('status')
    hospital_id = request.form.get('hospital_id', type=int)

    if new_status in ('In Storage', 'Reserved', 'Issued', 'Quarantined', 'Discarded', 'Expired'):
        old_status = unit.status
        unit.status = new_status
        if new_status == 'Issued':
            unit.issued_at = datetime.now(timezone.utc)
            if hospital_id:
                unit.issued_to_hospital_id = hospital_id
        db.session.commit()
        flash(f'Unit #{unit.unit_number} status updated from [{old_status}] to [{new_status}].', 'success')
    else:
        flash('Invalid unit status.', 'danger')

    return redirect(request.referrer or url_for('admin.qr_tracker'))


@admin_bp.route('/blood-unit/register', methods=['POST'])
def register_blood_bag():
    blood_group = request.form.get('blood_group', '').strip().upper()
    donor_id = request.form.get('donor_id', type=int) or None
    component_type = request.form.get('component_type', 'Packed Red Blood Cells').strip()
    volume_ml = request.form.get('volume_ml', type=int) or 450
    shelf_days = request.form.get('shelf_days', type=int) or 35
    screening = request.form.get('screening', 'HIV: Non-Reactive | HBV: Non-Reactive | HCV: Non-Reactive | Syphilis: Non-Reactive')
    storage_loc = request.form.get('storage_location', 'Cold Vault Compartment A')

    # Generate unique unit number
    count = BloodBagUnit.query.count() + 1
    unit_number = f"LS-UNIT-{datetime.now().year}-{count:04d}"

    expiry_date = date.today() + timedelta(days=shelf_days)

    new_unit = BloodBagUnit(
        unit_number=unit_number,
        blood_group=blood_group,
        donor_id=donor_id,
        component_type=component_type,
        volume_ml=volume_ml,
        collection_date=date.today(),
        expiry_date=expiry_date,
        screening_results=screening,
        storage_location=storage_loc,
        status='In Storage'
    )
    db.session.add(new_unit)

    # Sync inventory count
    inv = BloodInventory.query.filter_by(blood_group=blood_group).first()
    if inv:
        inv.units_available += 1
        inv.last_updated = datetime.now(timezone.utc)

    db.session.commit()
    flash(f'Sterile Blood Bag Unit #{unit_number} ({blood_group}) registered and QR code generated!', 'success')
    return redirect(url_for('admin.qr_tracker'))

