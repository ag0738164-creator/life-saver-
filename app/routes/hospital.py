from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import BloodRequest, BloodInventory
from app.routes import hospital_required

hospital_bp = Blueprint('hospital', __name__)

@hospital_bp.before_request
@login_required
@hospital_required
def hospital_guard():
    pass


@hospital_bp.route('/dashboard')
def dashboard():
    requests_query = current_user.blood_requests
    all_requests = requests_query.order_by(BloodRequest.created_at.desc()).all()
    
    total_requested_units = sum(r.units_requested for r in all_requests)
    pending_count = sum(1 for r in all_requests if r.status == 'Pending')
    approved_count = sum(1 for r in all_requests if r.status in ('Approved', 'Dispensed'))
    rejected_count = sum(1 for r in all_requests if r.status == 'Rejected')

    inventory = BloodInventory.query.order_by(BloodInventory.blood_group).all()

    return render_template(
        'hospital/dashboard.html',
        recent_requests=all_requests[:6],
        total_requests=len(all_requests),
        total_requested_units=total_requested_units,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        inventory=inventory
    )


@hospital_bp.route('/request', methods=['GET', 'POST'])
def request_blood():
    inventory = BloodInventory.query.order_by(BloodInventory.blood_group).all()

    if request.method == 'POST':
        blood_group = request.form.get('blood_group', '').strip().upper()
        units_requested = request.form.get('units_requested', type=int)
        urgency = request.form.get('urgency', 'Normal').strip()
        patient_name = request.form.get('patient_name', '').strip()
        patient_case_no = request.form.get('patient_case_no', '').strip()
        reason = request.form.get('reason', '').strip()

        # Validation
        if not blood_group or not units_requested or not patient_name:
            flash('Blood group, units, and patient name are required fields.', 'danger')
            return render_template('hospital/request_blood.html', inventory=inventory)

        if units_requested <= 0 or units_requested > 25:
            flash('Units requested must be between 1 and 25 units.', 'warning')
            return render_template('hospital/request_blood.html', inventory=inventory)

        # Check stock advisory (does not block submission, but warns hospital if current stock is low)
        stock_item = BloodInventory.query.filter_by(blood_group=blood_group).first()
        available_units = stock_item.units_available if stock_item else 0

        new_request = BloodRequest(
            hospital_id=current_user.id,
            blood_group=blood_group,
            units_requested=units_requested,
            urgency=urgency,
            patient_name=patient_name,
            patient_case_no=patient_case_no,
            reason=reason,
            status='Pending'
        )
        db.session.add(new_request)
        db.session.commit()

        if available_units < units_requested:
            flash(
                f'Requisition #{new_request.id} for {units_requested} unit(s) of {blood_group} submitted. Note: Current stock ({available_units} units) is below requested amount; the blood bank will prioritize replenishment.',
                'warning'
            )
        else:
            flash(
                f'Requisition #{new_request.id} for {units_requested} unit(s) of {blood_group} submitted successfully with priority [{urgency}].',
                'success'
            )

        return redirect(url_for('hospital.history'))

    return render_template('hospital/request_blood.html', inventory=inventory)


@hospital_bp.route('/history')
def history():
    status_filter = request.args.get('status', 'All')
    query = current_user.blood_requests
    if status_filter and status_filter != 'All':
        query = query.filter_by(status=status_filter)
    
    requests = query.order_by(BloodRequest.created_at.desc()).all()
    return render_template('hospital/history.html', requests=requests, status_filter=status_filter)


@hospital_bp.route('/receipt/<request_id>')
def receipt(request_id):
    req = BloodRequest.query.filter_by(id=request_id, hospital_id=current_user.id).first_or_404()
    return render_template('hospital/receipt.html', req=req)
