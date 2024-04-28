from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout

from django.http import Http404

from rest_framework import status
from rest_framework.response import Response

from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.decorators import api_view, permission_classes
from rest_framework.authentication import BasicAuthentication, TokenAuthentication
# from .permissions import IsAdminOrOwner
from bson import json_util
# Create your views here.
import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId 
# Start of the block

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["mydb"]
# End of the block


# Start of the block

org_attrs = ['email', 'password', 'org_id', 'license_id', 'org_status', 'org_type', 'org_name', 'org_fin_id', 'finan_limit_from', 'finan_limit_to', 'bank_account', 'org_attch']
cust_attrs = ["org_id", "org_name","org_admin_id", "permission_id","user_status", "bus_user_id1", "username", "email", "password", "user_attch"]
perm_attrs = ['email', 'password', 'perm_id', 'org_id', 'org_name', 'org_admin_id', 'user_status', 'super_admin', 'org_admin', 'merchant', 'service_agent' , 'field_agent', 'inventory_worker', 'consumer']

org_mand = ['email', 'password', 'org_id', 'license_id', 'org_status', 'org_type', 'org_name']
cust_mand = ["org_id", "org_admin_id", "permission_id", "user_status", "username", "email", "password", "user_attch"]
perm_mand = ['email', 'password', 'perm_id', 'org_id',  'org_admin_id', 'user_status', 'super_admin', 'org_admin',]
# End of the block

# Start of the block

def check_perm_attr(data):
    that_are_none = {}
    for x in perm_mand:
        if not data.get(x):
            that_are_none[x] = f"that is null"
    return that_are_none

def check_org_attr(data):
    that_are_none = {}
    for x in org_mand:
        if not data.get(x):
            that_are_none[x] = f"that is null"
    return that_are_none

def check_cust_attr(data):
    that_are_none = {}
    for x in cust_mand:
        if not data.get(x):
            that_are_none[x] = f"that is null"
    return that_are_none

def json_perm_data(data):
    document = {}
    for attr in perm_attrs:
        document[attr] = data.get(attr)
    return json_util.loads(json_util.dumps(document))

def json_org_data(data):
    document = {}
    for attr in org_attrs:
        document[attr] = data.get(attr)
    return json_util.loads(json_util.dumps(document))

def json_cust_data(data):
    document = {}
    for attr in cust_attrs:
        document[attr] = data.get(attr)
    return json_util.loads(json_util.dumps(document))

# End of the block

# ======================================================================================================================================================
# = Registration =======================================================================================================================================
# ======================================================================================================================================================


@api_view(['POST'])
def signin(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({'error': 'Both username and password are required'}, status=status.HTTP_400_BAD_REQUEST)


    print(request.data)
    print(username, password)

    user = authenticate(request, username=username, password=password)

    print("user", user)
    if user is not None:
        login(request, user)
        token, created = Token.objects.get_or_create(user=user)
        return Response({'message': 'Authentication successful', 'token': token.key}, status=status.HTTP_200_OK)
    
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
def signup(request):
    data = request.data
    
    if data.get('user_type') == 'organization':
        ret = check_org_attr(data)
        if ret:
            return Response(ret, status=status.HTTP_400_BAD_REQUEST)
        email, password, username = data.get('email'), data.get('password'), data.get('org_name')
        
        user = User.objects.create_user(username=email, email=email, password=password)
        user.save()

        document = json_org_data(data)
        print(document)

        collection = db['organizations']
        
        result = collection.insert_one(document)

        return Response({"data": data, "_id": str(result.inserted_id)})

    elif data.get('user_type') == 'customer':
        ret = check_cust_attr(data)
        if ret:
            return Response(ret, status=status.HTTP_400_BAD_REQUEST)
        

        email, password, username = data.get('email'), data.get('password'), data.get('username')

        user = User.objects.create_user(username=email, email=email, password=password)
        user.save()

        document = json_cust_data(data)

        collection = db['users']
        result = collection.insert_one(document)
        return Response({"data": data, "_id": str(result.inserted_id)})
    

    elif data.get('user_type') == 'permission':
        ret = check_perm_attr(data)
        if ret:
            return Response(ret, status=status.HTTP_400_BAD_REQUEST)
        email, password, username = data.get('email'), data.get('password'), data.get('org_name')

        user = User.objects.create_user(username=email, email=email, password=password)

        user.save()

        document = json_cust_data(data)

        collection = db['permissions']
        result = collection.insert_one(document)
        return Response({"data": data, "_id": str(result.inserted_id)})

    return Response({'err': 'error', 'user_type': 'required'},)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def signout(request):
    username = request.user
    logout(request)
    return Response({
        "message": f"logout {username} successfully"
    }, status=status.HTTP_200_OK)

# ======================================================================================================================================================
# = Single Level  ======================================================================================================================================
# ======================================================================================================================================================


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user(request, pk):
    collection = db['users']
    if request.method == 'GET':
        try:
            document = collection.find_one({'_id': ObjectId(pk)})
            document = { f'{doc}': f'{document[doc]}' for doc in document}
        except:
            return Response({"error": f'{pk} not exist'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({"document": document}, status=status.HTTP_200_OK)

    if request.method == 'PUT':
        data = request.data

        # to prevent update email & password
        try:
            data.pop('email')
            data.pop('password')
            data.pop('_id') # id is immutable
        except:
            pass


        try:
            result = collection.update_one({'_id': ObjectId(pk)}, {'$set': data})
        except:
            return Response({'error': 'Error in Trying update user. id may be not exist !'}, status=status.HTTP_404_NOT_FOUND)

        if result.modified_count > 0:
            return Response({'message': 'Document updated successfully'}, status=status.HTTP_202_ACCEPTED)
        else:
            return Response({'error': 'No changes made or Document not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def organization(request, pk):

    collection = db['organizations']
    if request.method == 'GET':

        try:
            document = collection.find_one({'_id': ObjectId(pk)})
            document = { f'{doc}': f'{document[doc]}' for doc in document}
        except:
            return Response({"error": f'{pk} not exist'}, status=status.HTTP_404_NOT_FOUND)

        return Response({"document": document}, status=status.HTTP_200_OK)

    if request.method == 'PUT':
        data = request.data
        # to prevent update email & password
        try:
            data.pop('email')
            data.pop('password')
            data.pop('_id') # id is immutable
        except:
            pass

        try:
            result = collection.update_one({'_id': ObjectId(pk)}, {'$set': data})
        except:
            return Response({'error': 'Error in Trying update organization. id may be not exist !'}, status=status.HTTP_404_NOT_FOUND)

        if result.modified_count > 0:
            return Response({'message': 'Document updated successfully'}, status=status.HTTP_202_ACCEPTED)
        else:
            return Response({'error': 'Document not found or no changes made'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def permission(request, pk):

    collection = db['permissions']
    if request.method == 'GET':
        try:
            document = collection.find_one({'_id': ObjectId(pk)})
            document = { f'{doc}': f'{document[doc]}' for doc in document}
        except:
            return Response({"error": f'{pk} not exist'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({"document": document})

    if request.method == 'PUT':
        data = request.data
        # to prevent update email & password
        try:
            data.pop('email')
            data.pop('password')
            data.pop('_id') # id is immutable
        except:
            pass

        try:
            result = collection.update_one({'_id': ObjectId(pk)}, {'$set': data})
        except:
            return Response({'error': 'Error in Trying update permission. id may be not exist !'}, status=status.HTTP_404_NOT_FOUND)

        if result.modified_count > 0:
            return Response({'message': 'Document updated successfully'}, status=status.HTTP_202_ACCEPTED)
        else:
            return Response({'error': 'Document not found or no changes made'}, status=status.HTTP_404_NOT_FOUND)


# ======================================================================================================================================================
# = list Level  ========================================================================================================================================
# ======================================================================================================================================================


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def users_list(request):
    collection = db['users']

    if request.method == 'GET':
        cursor = collection.find()

        # documents_list = [{ f"{at}": document[at] for at in cust_attrs} for document in cursor]
        documents_list = []

        for document in cursor:
            user_detail = {}
            
            for at in cust_attrs:
                try:
                    user_detail[at] = document[at]
                except:
                    pass
            if user_detail:
                user_detail['_id'] = f"{document['_id']}"
                documents_list.append(user_detail)


        print(documents_list)
        return Response({"data": documents_list}, status=status.HTTP_202_ACCEPTED)
    
    if request.method == 'PUT':
        ids_not_updated_its_document = []
        documents = request.data
        for document in documents:
            # to prevent update email & password
            try:
                document.pop('email')
                document.pop('password')
            except:
                pass
            try:
                pk = document.pop('_id')
            except:
                return Response({'error': 'some documents without _id'}, status=status.HTTP_404_NOT_FOUND)
            
            print(document) 
            print(pk)
            try:
                result = collection.update_one({'_id': ObjectId(pk)}, {'$set': document})
            except:
                ids_not_updated_its_document.append(pk)
                return Response({'error': 'Error in Trying update many users', '_id_not_found': pk}, status=status.HTTP_404_NOT_FOUND)
            # break
        return Response({"Right": 'Allah Is Only One.'}, status=status.HTTP_202_ACCEPTED)

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def organizations_list(request):
    collection = db['organizations']

    if request.method == 'GET':
        cursor = collection.find()

        documents_list = []

        for document in cursor:
            org_detail = {}
            
            for at in org_attrs:
                try:
                    org_detail[at] = document[at]
                except:
                    pass

            if org_detail:
                org_detail['_id'] = f"{document['_id']}"
                documents_list.append(org_detail)

        print(documents_list)
        return Response({"data": documents_list}, status=status.HTTP_202_ACCEPTED)

    if request.method == 'PUT':
        ids_not_updated_its_document = []
        documents = request.data
        for document in documents:
            # to prevent update email & password
            try:
                document.pop('email')
                document.pop('password')
            except:
                pass
            try:
                pk = document.pop('_id')
            except:
                return Response({'error': 'some documents without _id'}, status=status.HTTP_404_NOT_FOUND)
            
            print(document) 
            print(pk)
            try:
                result = collection.update_one({'_id': ObjectId(pk)}, {'$set': document})
            except:
                ids_not_updated_its_document.append(pk)
                return Response({'error': 'Error in Trying update many orgnazations', '_id_not_found': pk}, status=status.HTTP_404_NOT_FOUND)
            # break
        return Response({"Right": 'Allah Is Only One.'}, status=status.HTTP_202_ACCEPTED)

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def permissions_list(request):
    collection = db['permissions']

    if request.method == 'GET':
        cursor = collection.find()

        documents_list = []

        for document in cursor:
            perm_detail = {}
            
            for at in perm_attrs:
                try:
                    perm_detail[at] = document[at]
                except:
                    pass
            if perm_detail:
                perm_detail['_id'] = f"{document['_id']}"
                documents_list.append(perm_detail)

        print(documents_list)
        return Response({"data": documents_list}, status=status.HTTP_202_ACCEPTED)
    
    if request.method == 'PUT':
        ids_not_updated_its_document = []
        documents = request.data
        for document in documents:
            # to prevent update email & password
            try:
                document.pop('email')
                document.pop('password')
            except:
                pass

            try:
                pk = document.pop('_id')
            except:
                return Response({'error': 'some documents without _id'}, status=status.HTTP_404_NOT_FOUND)
            
            print(document) 
            print(pk)
            try:
                result = collection.update_one({'_id': ObjectId(pk)}, {'$set': document})
            except:
                ids_not_updated_its_document.append(pk)
                return Response({'error': 'Error in Trying update many permissions', '_id_not_found': pk}, status=status.HTTP_404_NOT_FOUND)
            # break
        return Response({"Right": 'Allah Is Only One.'}, status=status.HTTP_202_ACCEPTED)

# ======================================================================================================================================================
# ======================================================================================================================================================
# ======================================================================================================================================================
