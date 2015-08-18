import os
from flask import Flask, abort, request, jsonify, g, url_for
from flask.ext.httpauth import HTTPBasicAuth
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
import xmlrpclib
from xmlrpclib import Error
import sys

user = 'admin'
pwd = 'P@ssw0rd'
dbname = 'rdm_dev'
server = 'localhost'
port = '8069'

# initialization
app = Flask(__name__)
app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy dog'
# extensions
auth = HTTPBasicAuth()



class Member():
    
    def __init__(self, customer):
        self.customer = customer
    
    def generate_auth_token(self, expiration=600):
        s = Serializer(app.config['SECRET_KEY'], expires_in=expiration)
        return s.dumps({'id': self.customer['id']})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None    # valid token, but expired
        except BadSignature:
            return None    # invalid token
        
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
        uid = sock.login(dbname , user , pwd)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')                
        args = [('id','=',data['id'])]            
        ids = sock.execute(dbname, uid, pwd, 'rdm.customer', 'search', args)  
        fields = []
        partner = sock.execute(dbname, uid, pwd, 'rdm.customer', 'read', ids[0], fields)                
        return Member(partner)

@auth.verify_password
def verify_password(username_or_token, password):
    # first try to authenticate by token
    member = Member.verify_auth_token(username_or_token)
    if not member:
        # try to authenticate with username/password
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
        uid = sock.login(dbname , user , pwd)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')                
        args = [('email','=',username_or_token)]            
        ids = sock.execute(dbname, uid, pwd, 'rdm.customer', 'search', args)
        if not ids: 
            return False
        fields= []
        customer = sock.execute(dbname, uid, pwd, 'rdm.customer', 'read', ids[0], fields)
        member = Member(customer)
    g.member = member
    return True

@app.route('/api/v1/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
    uid = sock.login(dbname , user , pwd)
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')                
    args = [('email','=',username),('password','=',password)]            
    ids = sock.execute(dbname, uid, pwd, 'rdm.customer', 'search', args)  
    if not ids:
        abort(400)
    fields = []
    customer = sock.execute(dbname, uid, pwd, 'rdm.customer', 'read', ids[0], fields)
    member = Member(customer)
    return jsonify({'success':True,'result':[{'username': member.customer['email'],'contact_type':member.customer['contact_type']}]})
    #return '{"username":"' +  member.customer['email'] + '"}'
    
@app.route('/api/users/<int:id>')
def get_user(id):    
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
    uid = sock.login(dbname , user , pwd)
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')                
    args = [('id','=',id)]            
    ids = sock.execute(dbname, uid, pwd, 'res.partner', 'search', args)  
    if not ids:
        abort(400)
    fields = []
    partner = sock.execute(dbname, uid, pwd, 'res.partner', 'read', ids[0], fields)
    return jsonify({'username': partner['email']})


@app.route('/api/v1/token')
@auth.login_required
def get_auth_token():
    token = g.member.generate_auth_token(600)
    return jsonify({'token': token.decode('ascii'), 'duration': 600})
    
@app.route('/testapi')
def testapi():
    list = [
        {'param':'foo','val':2},
        {'param':'bar','val':10},
    ]    
    return jsonify(results=list)


@app.route('/api/v1/provincedropdown')
@auth.login_required
def provincedropdown():    
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
    uid = sock.login(dbname , user , pwd)
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')    
    args = []
    ids = sock.execute(dbname, uid, pwd, 'rdm.province', 'search', args)  
    if ids:
        fields = ['name']
        data = sock.execute(dbname, uid, pwd, 'rdm.province', 'read', ids, fields)                                 
        return jsonify(success='true',results=data)

@app.route('/api/v1/citydropdown')
@auth.login_required
def citydropdown():    
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
    uid = sock.login(dbname , user , pwd)
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')    
    args = []
    ids = sock.execute(dbname, uid, pwd, 'rdm.city', 'search', args)  
    if ids:
        fields = ['name']
        data = sock.execute(dbname, uid, pwd, 'rdm.city', 'read', ids, fields)                                 
        return jsonify(success='true',results=data)
    
@app.route('/api/v1/customer')
@auth.login_required
def customer():
    if request.method == 'GET':
        customer_id = g.member.customer['id']        
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
        uid = sock.login(dbname , user , pwd)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')    
        args = [('id','=', int(customer_id))]
        ids = sock.execute(dbname, uid, pwd, 'rdm.customer', 'search', args)  
        if ids:
            fields = ['ayc_number', 'name', 'birth_place', 'birth_date', 'social_id', 'address', 'city' ,'province', 'zipcode', 'phone1', 'phone2', 'mobile_phone1', 'mobile_phone2', 'email', 'coupon','point','tenant_id']
            data = sock.execute(dbname, uid, pwd, 'rdm.customer', 'read', [ids[0]], fields)                                 
    return jsonify(success='true',message='',results=data)

@app.route('/api/v1/changecustomer')
@auth.login_required
def changecustomer():
    if request.method == 'GET':           
        customer_id = g.member.customer['id']     
        address = request.args['address']
        city = request.args['city']
        province = request.args['province']        
        zipcode = request.args['zipcode']
        phone1 = request.args['phone1']
        phone2 = request.args['phone2']
        mobile_phone1 = request.args['mobile_phone1']
        mobile_phone2 = request.args['mobile_phone2']
        
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
        uid = sock.login(dbname , user , pwd)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')    
        args = [('id','=', int(customer_id))]
        ids = sock.execute(dbname, uid, pwd, 'rdm.customer', 'search', args)  
        if ids:
            values = {}
            values.update({'address':address})
            values.update({'city':city})
            values.update({'province':province})
            values.update({'zipcode':zipcode})
            values.update({'phone1':phone1})
            values.update({'phone2':phone2})
            values.update({'mobile_phone1':mobile_phone1})
            values.update({'mobile_phone2':mobile_phone2})
            result = sock.execute(dbname, uid, pwd, 'rdm.customer', 'write', ids, values)
            return jsonify(success='true',message='Data Saved Succesfully',results=[])
        else:
            return jsonify(success='false',message='Data not Saved',results=[])                             
    
@app.route('/api/v1/changepassword')
@auth.login_required
def changepassword():
    if request.method == 'GET':        
        customer_id = g.member.customer['id']
        old_password = request.args['old_password']
        new_password = request.args['new_password']        
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
        uid = sock.login(dbname , user , pwd)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')    
        args = [('id','=', int(customer_id)),('password','=', old_password)]
        ids = sock.execute(dbname, uid, pwd, 'rdm.customer', 'search', args)      
        if ids:
            data={}
            data.update({'password':new_password})
            results = sock.execute(dbname, uid, pwd, 'rdm.customer', 'write', ids, data) 
            return jsonify(success='true',message='Change Password Successfully',results=[])  
        else:
            return jsonify(success='false',message='Change Password Failed or Old Password Wrong',results=[])
                  
@app.route('/api/v1/requestchangepassword')           
def requestchangepassword():
    if request.method == 'GET':
        email = request.args['email']
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
        uid = sock.login(dbname , user , pwd)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')    
        args = [('email','=', email)]
        ids = sock.execute(dbname, uid, pwd, 'rdm.customer', 'search', args)      
        if ids:
            data = {}
            data.update({'state':'request_change_password'})
            results = sock.execute(dbname, uid, pwd, 'rdm.customer', 'write', ids, data)
            if results:
                return jsonify(success='true',message='Request Change Password Successfully',results=[])
            else:
                return jsonify(success='false',message='Request Change Password Failed',results=[])
        else:
            return jsonify(success='false',message='Request Change Password Failed',results=[])

@app.route('/api/v1/resetpassword')           
def resetpassword():
    if request.method == 'GET':
        customer_id = request.args['customer_id']
        passcode = request.args['passcode']
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
        uid = sock.login(dbname , user , pwd)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')    
        args = [('id','=', int(customer_id)),('request_change_password_passcode','=',passcode),('request_change_password','=',True)]
        ids = sock.execute(dbname, uid, pwd, 'rdm.customer', 'search', args)              
        if ids:
            data = {}
            data.update({'state':'reset_password'})
            results = sock.execute(dbname, uid, pwd, 'rdm.customer', 'write', ids, data)
            if results:
                return jsonify(success='true',message='Reset Password Successfully',results=[])
            else:
                return jsonify(success='false',message='Reset Password Failed',results=[])
        else:
            return jsonify(success='false',message='Reset Password Failed',results=[])

        
@app.route('/api/v1/custtrans')
@auth.login_required
def custtrans():    
    customer_id = g.member.customer['id']
    start_date = request.args['start_date']
    end_date = request.args['end_date']
    #start_date = '2015-07-01'
    #end_date = '2015-07-30'
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
    uid = sock.login(dbname , user , pwd)
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')    
    args = [('customer_id','=', int(customer_id)),('trans_date','>=', start_date),(['trans_date','<=', end_date])]
    ids = sock.execute(dbname, uid, pwd, 'rdm.trans', 'search', args)
    if not ids:
        abort(400)    
    fields = ['trans_id','trans_date','total_amount','total_item']            
    data = sock.execute(dbname, uid, pwd, 'rdm.trans', 'read', ids, fields)                
    return jsonify(success='true',results=data)

@app.route('/api/v1/tenant')
@auth.login_required
def tenant():
    if request.method == 'GET':
        tenant_id = request.args['id']
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
        uid = sock.login(dbname , user , pwd)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')    
        args = [('id','=', int(tenant_id))]
        ids = sock.execute(dbname, uid, pwd, 'rdm.tenant', 'search', args)  
        if ids:
            fields = ['name']
            data = sock.execute(dbname, uid, pwd, 'rdm.tenant', 'read', [ids[0]], fields)                         
        
    return jsonify(success='true',results=data)

@app.route('/api/v1/reward')
@auth.login_required
def reward():
    if request.method == 'GET':
        reward_id = request.args['reward_id']
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
        uid = sock.login(dbname , user , pwd)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')    
        args = [('id','=', int(reward_id))]
        ids = sock.execute(dbname, uid, pwd, 'rdm.reward', 'search', args)  
        if ids:
            fields = []
            data = sock.execute(dbname, uid, pwd, 'rdm.reward', 'read', [ids[0]], fields)                         
    return jsonify(success='true',results=data)


@app.route('/api/v1/readreward')
@auth.login_required
def readreward():
    if request.method == 'GET':
        reward_id = request.args['reward_id']
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
        uid = sock.login(dbname , user , pwd)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')    
        args = [('id','=', int(reward_id))]
        ids = sock.execute(dbname, uid, pwd, 'rdm.reward', 'search', args)  
        if ids:
            fields = ['point']
            data = sock.execute(dbname, uid, pwd, 'rdm.reward', 'read', [ids[0]], fields)                         
    return jsonify(success='true',results=data)

@app.route('/api/v1/rewardimage')
@auth.login_required
def rewardimage():
    if request.method == 'GET':
        reward_id = request.args['reward_id']
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
        uid = sock.login(dbname , user , pwd)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')    
        args = [('id','=', reward_id)]
        ids = sock.execute(dbname, uid, pwd, 'rdm.reward', 'search', args)  
        if ids:
            fields = ['image1']
            data = sock.execute(dbname, uid, pwd, 'rdm.reward', 'read', [ids[0]], fields)                         
            return jsonify(success='true',message='',results=data)
        else:
            return jsonify(success='false',message='',results=data)

        
@app.route('/api/v1/rewarddropdown')
@auth.login_required
def rewarddropdown():    
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
    uid = sock.login(dbname , user , pwd)
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')    
    args = [('state','=','draft')]
    ids = sock.execute(dbname, uid, pwd, 'rdm.reward', 'search', args)  
    if ids:
        fields = ['name']
        data = sock.execute(dbname, uid, pwd, 'rdm.reward', 'read', ids, fields)                                 
        return jsonify(success='true',results=data)
    
@app.route('/api/v1/bookingreward')
@auth.login_required
def bookingreward():        
    if request.method == 'GET':        
        customer_id = g.member.customer['id']        
        reward_id = request.args['reward_id']
        print str(customer_id)
        print str(reward_id)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
        uid = sock.login(dbname , user , pwd)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')
        values = {}
        values.update({'customer_id':int(str(customer_id))})
        values.update({'reward_id':int(str(reward_id))})
        values.update({'is_booking': True})
        try:            
            result = sock.execute(dbname, uid, pwd, 'rdm.reward.trans', 'create', values)
            if result:
                return jsonify(success="true",results=[], message='Data Saved Successfully')
            else:
                return jsonify(success="false",results=[], message='Error Booking Reward')                    
        except Error as err:
            print err                            
            return jsonify(success="false",results=[], message='Error Booking Reward')     

@app.route('/api/v1/myreward')
@auth.login_required
def myreward():        
    if request.method == 'GET':        
        customer_id = g.member.customer['id']
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
        uid = sock.login(dbname , user , pwd)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')    
        args = [('customer_id','=', int(customer_id))]
        ids = sock.execute(dbname, uid, pwd, 'rdm.reward.trans', 'search', args)
        if ids:
            fields = ['trans_id','trans_date','reward_id']            
            data = sock.execute(dbname, uid, pwd, 'rdm.reward.trans', 'read', ids, fields)
            try:                
                return jsonify(success='true',results=data)                   
            except Error as err:
                print err
                return jsonify(success='false',results=[])            
        return jsonify(success='false',results=[])
    
@app.route('/api/v1/usulan')
@auth.login_required
def usulan():        
    if request.method == 'GET':
        customer_id = request.args['customer_id']
        category_id = request.args['category_id']
        subject = request.args['subject']
        description = request.args['description']                
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
        uid = sock.login(dbname , user , pwd)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')    
        args = [('id','=', int(customer_id))]
        ids = sock.execute(dbname, uid, pwd, 'rdm.customer', 'search', args)  
        if ids:
            fields = ['tenant_id']
            customer = sock.execute(dbname, uid, pwd, 'rdm.customer', 'read', ids, fields)
            values = {}
            values.update({'tenant_id':customer[0].get('tenant_id')[0]})            
            values.update({'customer_id':customer_id})
            values.update({'message_category_id':category_id})
            values.update({'subject':subject})
            values.update({'message':description})
            result = sock.execute(dbname, uid, pwd, 'rdm.tenant.message', 'create', values)
            return jsonify(success='true',message='Data Saved Succesfully',results=[])
        else:
            return jsonify(success='false',message='Error while saving',results=[])

@app.route('/api/v1/messagecategorydropdown')
@auth.login_required
def messagecategorydropdown():    
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
    uid = sock.login(dbname , user , pwd)
    sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')    
    args = []
    ids = sock.execute(dbname, uid, pwd, 'rdm.tenant.message.category', 'search', args)  
    if ids:
        fields = ['name']
        data = sock.execute(dbname, uid, pwd, 'rdm.tenant.message.category', 'read', ids, fields)                                 
        return jsonify(success='true',results=data)
    
@app.route('/api/v1/usulanlist')
@auth.login_required
def usulanlist():
    if request.method == 'GET':
        customer_id = request.args['customer_id']
        
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port +'/xmlrpc/common')
        uid = sock.login(dbname , user , pwd)
        sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')    
        args = [('id','=', int(customer_id))]
        
        ids = sock.execute(dbname, uid, pwd, 'rdm.customer', 'search', args)
        if ids:
            fields = ['tenant_id']
            customer = sock.execute(dbname, uid, pwd, 'rdm.customer', 'read', ids, fields)            
            args = [('tenant_id','=',customer[0].get('tenant_id')[0])]            
            message_ids = sock.execute(dbname, uid, pwd, 'rdm.tenant.message', 'search', args)            
            fields = ['trans_date', 'customer_id', 'message_category_id', 'subject', 'message','state']
            data = sock.execute(dbname, uid, pwd, 'rdm.tenant.message', 'read', message_ids, fields)             
            return jsonify(success='true',results=data)
        else:
            jsonify(success='false',results=[])                  
                               
    return jsonify(success='false',results=[])


if __name__ == "__main__":
    app.run()