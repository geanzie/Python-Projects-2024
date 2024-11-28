from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from .forms import UserRegistrationForm
from django.views.generic import ListView, DetailView, TemplateView, UpdateView
from .models import Document, DocumentActivity, DocumentStatus, Department, ResponsibilityCenter
from django.views import View
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .forms import DocumentForm  # Assuming you have a form for Document model
from django.db.models import Q, Count, Max, Subquery, OuterRef, F, Case, When, Value, IntegerField, Prefetch
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib.auth.forms import UserCreationForm
from django.views.generic.edit import CreateView
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from .models import Profile
from .forms import UserRegistrationForm, DocumentStatusUpdateForm, AccountingForm  # Ensure this is your custom form with the department field
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.db import IntegrityError
from django.db import transaction
from django.contrib.auth.models import User
from .models import DocumentActivity
from django.core.paginator import Paginator
from datetime import datetime
from decimal import Decimal


# User Registration View
class UserRegistrationView(View):
    def get(self, request):
        form = UserRegistrationForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Save the user object without committing to the database yet
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])  # Set the password

            # Save the user object
            user.save()

            # Check if department was passed and assign to profile
            department = form.cleaned_data['department']
            if department:
                profile, created = Profile.objects.get_or_create(user=user)
                profile.department = department
                profile.save()
                print(f"Department {department.name} assigned to user.")
            else:
                print("No department selected.")
            
            return redirect('login')  # Redirect to the login page after successful registration
        return render(request, 'accounts/register.html', {'form': form})


class UserLoginView(LoginView):
    template_name = 'accounts/login.html'
    success_url = reverse_lazy('dashboard')  # Redirect to dashboard after successful login

    # You can override form_valid() to capture user-specific session handling if needed
    def form_valid(self, form):
        response = super().form_valid(form)
        # Set session timeout here if needed or additional logic
        return response


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('login')  # Redirect to login page after logout

    # You can override get() here to log the user out based on some custom logic if needed
    def get(self, request, *args, **kwargs):
        logout(request)
        return super().get(request, *args, **kwargs)
from .models import ResponseCenter
class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'tracking/document_form.html'
    success_url = reverse_lazy('document_list')

    def form_valid(self, form):
        print("Inside form_valid method")  # Check if this method is executed

        # Check if the form is valid
        if not form.is_valid():
            print(f"Form errors: {form.errors}")  # Output form errors
            return self.form_invalid(form)
        else:
            print("Form is valid")  # Confirm the form is valid

        # Retrieve the user's department
        user_department = getattr(self.request.user.profile, 'department', None)
        print(f"User's department: {user_department}")  # Output user's department

        if not user_department:
            print("No department found in user's profile")  # Output error if no department
            messages.error(self.request, "Your profile does not have an assigned department.")
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                print("Starting transaction")  # Indicate start of transaction
                
                # Attempt to save the document
                document = form.save(commit=False)
                document.initial_department = user_department
                document.status = 'In Process'
                print(f"Document to save: {document}")  # Output document data before saving
                document.save()
                print(f"Document saved with ID: {document.id}")  # Confirm document save

                if document.id:
                    DocumentStatus.objects.create(
                        document=document,
                        department=document.initial_department,
                        status=document.status
                    )
                    print("DocumentStatus entry created")  # Confirm DocumentStatus creation

                    DocumentActivity.objects.create(
                        document=document,
                        action="Created",
                        performed_by=self.request.user,
                        timestamp=document.created_at
                    )
                    print("DocumentActivity entry created")  # Confirm DocumentActivity creation

                    # Save Responsibility Center and Amount entries
                    responsibility_centers = self.request.POST.getlist('responsibility_center[]')  # Get all responsibility center codes
                    amounts = self.request.POST.getlist('amount[]')  # Get all corresponding amounts

                    for rc_code, amount in zip(responsibility_centers, amounts):
                        ResponsibilityCenter.objects.create(
                            rc_code=rc_code,
                            amount=amount,
                            document=document
                        )
                    print("ResponsibilityCenter entries created")  # Confirm ResponsibilityCenter creation
                    
                else:
                    print("Document save failed - No document ID")  # Output error if document not saved
                    raise IntegrityError("Document save failed - No document ID.")

            print("Transaction completed successfully")  # Confirm successful transaction
            return redirect(self.success_url)

        except IntegrityError as e:
            print(f"IntegrityError: {e}")  # Output IntegrityError
            messages.error(self.request, f"Error creating document: {str(e)}")
            return self.form_invalid(form)
        except Exception as ex:
            print(f"Unexpected error: {ex}")  # Output any other exception
            messages.error(self.request, "An unexpected error occurred while creating the document.")
            return self.form_invalid(form)
        
    def get_context_data(self, **kwargs):
        print("Inside get_context_data")  # Check if this method is executed
        context = super().get_context_data(**kwargs)
        context['form'] = DocumentForm()  # Provide a fresh form for the template
        context['responsibility_centers'] = ResponseCenter.objects.all()  # Include Responsibility Centers
        print("Context data set")  # Confirm context data setup
        return context


class DocumentEditView(LoginRequiredMixin, UpdateView):
    model = Document
    form_class = DocumentForm  # Form to use for editing
    template_name = 'tracking/document_edit.html'  # Path to the template
    context_object_name = 'document'
    success_url = reverse_lazy('document_list')  # Redirect to document list after saving

    def form_valid(self, form):
        # Save the document and log the activity
        messages.success(self.request, "Document updated successfully.")
        
        # Record activity
        DocumentActivity.objects.create(
            document=self.object,
            action="Edited",
            performed_by=self.request.user,
            timestamp=self.object.created_at
        )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        # Handle invalid form submission if needed
        messages.error(self.request, "There was an error updating the document.")
        return super().form_invalid(form)

    
class DocumentUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        status = request.POST.get('status')
        
        # Retrieve the previous department based on document history
        previous_department = self.get_previous_department(document)

        # Process status update based on the new status received
        if status == 'Forwarded':
            # Handle forwarding logic
            forwarded_to_id = request.POST.get('forwarded_to')
            forwarded_to_department = get_object_or_404(Department, id=forwarded_to_id)
            document.forward_document(forwarded_to_department)  # Assuming this is implemented correctly
            
            # Create a new DocumentStatus entry with 'Forwarded'
            DocumentStatus.objects.create(
                document=document,
                department=forwarded_to_department,
                status='Forwarded'
            )

            # Record activity
            DocumentActivity.objects.create(
                document=document,
                action="Forwarded",
                performed_by=request.user,
                timestamp=document.updated_at
            )

        elif status == 'Returned':
            # Handle return logic
            document.forwarded_to = None  # Clear forwarded_to field to indicate return to the previous department
            document.save(update_fields=['forwarded_to'])
            
            # Record the 'Returned' status for the previous department
            DocumentStatus.objects.create(
                document=document,
                department=previous_department,
                status='Returned'
            )

            # Record activity
            DocumentActivity.objects.create(
                document=document,
                action="Returned",
                performed_by=request.user,
                timestamp=document.updated_at
            )

        else:
            # Update status directly in the DocumentStatus table for the current department
            DocumentStatus.objects.update_or_create(
                document=document,
                department=document.forwarded_to or document.initial_department,
                defaults={'status': status}
            )

            # Record activity
            DocumentActivity.objects.create(
                document=document,
                action=f"Status changed to {status}",
                performed_by=request.user,
                timestamp=document.updated_at
            )

        # Display success message and redirect
        messages.success(request, 'Document status updated successfully.')
        return redirect('tracking:document_list')

    def get_previous_department(self, document):
        """
        Determine the previous department based on the latest document status in history.
        """
        last_status = document.statuses.order_by('-timestamp').first()  # Get the most recent status
        
        # Return the department associated with the last status if it exists
        if last_status:
            return last_status.department
        # Default to initial department if no history is found
        return document.initial_department

        
class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'track/document_list.html'
    context_object_name = 'documents'
    paginate_by = 10  # Adjust pagination limit as necessary

    def get_queryset(self):
        queryset = Document.objects.all()

        # Apply status filter from URL parameter
        status = self.request.GET.get('status', None)
        if status:
            queryset = queryset.filter(statuses__status=status)  # Use 'statuses' related field for filtering

        # Apply search filter if search_query is present
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(title__icontains=search_query)

        # Get the user's department from the profile
        user_department = self.request.user.profile.department if hasattr(self.request.user, 'profile') else None

        # Prefetch the related DocumentStatus objects and order by timestamp (get the latest status)
        document_statuses = Prefetch(
            'statuses',
            queryset=DocumentStatus.objects.order_by('-timestamp'),
            to_attr='latest_status'  # This will create an attribute for the latest status for each document
        )

        queryset = queryset.prefetch_related(document_statuses)

        # Order documents by their forwarded_to field (prioritize unforwarded and current department documents)
        queryset = queryset.order_by(
            Case(
                When(forwarded_to=None, then=0),  # Documents not forwarded yet will come first
                When(forwarded_to=user_department, then=0),  # Documents forwarded to the user's department
                default=1,  # Other documents come later
                output_field=IntegerField(),
            ),
            'payee'  # Optional: Sort by title or any other field
        )

        # Add custom status and the `can_receive` or `can_update_status` flags
        for document in queryset:
            # Get the most recent status from the 'latest_status' attribute
            latest_status = document.latest_status[0] if document.latest_status else None
            document.document_status = latest_status.status if latest_status else 'Unknown'

            # Set the `can_receive` flag for receiving documents in the 'Forwarded' state
            if latest_status and latest_status.status == 'Forwarded':
                document.can_receive = document.forwarded_to == user_department
            elif latest_status and latest_status.status == 'Received':
                document.can_update_status = document.forwarded_to == user_department
            else:
                document.can_receive = False

        return queryset

    def post(self, request, *args, **kwargs):
        # Handle 'Receive' button click
        document_id = request.POST.get('document_id')
        document = get_object_or_404(Document, id=document_id)

        # Check if the document is in 'Forwarded' status and is being received by the department
        document_status = DocumentStatus.objects.filter(document=document).order_by('-timestamp').first()
        if document_status and document_status.status == 'Forwarded' and document.forwarded_to == self.request.user.profile.department:
            # Update the status for the receiving department to 'Received'
            document_status.status = 'Received'
            document_status.save()

            # Create a new 'In Process' status for the receiving department
            DocumentStatus.objects.create(document=document, status='In Process', department=document.forwarded_to)

            messages.success(request, "Document received and status updated.")
        else:
            messages.error(request, "You are not authorized to receive this document.")

        return redirect('document_list')
    
class DashboardView(LoginRequiredMixin, View):

    def dispatch(self, request, *args, **kwargs):
        # Step 1: Check session for last activity timestamp
        last_activity = request.session.get('last_activity')
        if last_activity:
            # Convert the last activity string back to a datetime object
            last_activity_time = datetime.fromisoformat(last_activity)
            time_elapsed = timezone.now() - last_activity_time
            # Step 2: Timeout after 30 minutes of inactivity
            if time_elapsed > timedelta(minutes=30):
                logout(request)  # Log out the user
                return redirect('login')  # Redirect to login page
        # Step 3: Update the last activity timestamp in the session
        request.session['last_activity'] = timezone.now().isoformat()  # Store as string in ISO format
        
        # Continue with the regular request handling (calling the parent dispatch method)
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):

        # Step 1: Retrieve or set session data
        if 'last_dashboard_visit' not in request.session:
            request.session['last_dashboard_visit'] = 'First visit'
        else:
            last_visit = request.session['last_dashboard_visit']
            print(f"Last dashboard visit: {last_visit}")
        
        # Update the session with the current visit time
        request.session['last_dashboard_visit'] = str(timezone.now())
        
       # Get the logged-in user's department
        user_department = request.user.profile.department

        # Query all activities related to the user's department
        recent_activities = DocumentActivity.objects.filter(
            Q(document__initial_department=user_department) | 
            Q(document__forwarded_to=user_department) and 
            Q(performed_by=request.user.profile.user)
        ).select_related('document', 'performed_by').order_by('-timestamp')

        # Total number of actions performed by the logged-in user
        total_actions = recent_activities.count()

        # Group activities by action and count them
        activity_summary = recent_activities.values('action').annotate(
            action_count=Count('id')
        )

        # Initialize the status counts dictionary
        status_counts_dict = {
            'Total': 0,
            'Returned': 0,
            'Forwarded': 0,
            'Released': 0,
            'Received': 0,
        }

        # Update status counts
        for entry in activity_summary:
            action = entry['action'].replace(" ", "_")
            count = entry['action_count']
            if action in status_counts_dict:
                status_counts_dict[action] += count

        # Paginate recent activities
        paginator = Paginator(recent_activities, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Step 12: Prepare the context to pass to the template
        context = {
            'status_counts': status_counts_dict,  # Pass the status counts per department
            'recent_activities': page_obj,  # Pass the paginated recent activities
            'last_dashboard_visit': request.session.get('last_dashboard_visit', 'N/A'),  # Pass session data
            'total_documents': total_actions  # Add total documents to the contex
        }

        # Step 13: Render the dashboard template with the context data
        return render(request, 'dashboard.html', context)
        
class DashboardStatusListView(LoginRequiredMixin, View):
    def get(self, request):
        # Get the status from the query parameter
        status = request.GET.get('status')
        user_department = request.user.profile.department  # Assuming Profile model is linked to the User

        # Filter documents based on the logged-in user's department and the status
        documents = Document.objects.filter(
            Q(initial_department=user_department) | Q(forwarded_to=user_department)
        )

        if status:
            documents = documents.filter(current_status=status)

        # Pass the filtered documents and the status to the template
        context = {
            'documents': documents,
            'status': status,
        }
        return render(request, 'dashboard_status_list.html', context)
    
class UserRegisterView(View):
    def get(self, request):
        form = UserCreationForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful.')
            return redirect('login')
        return render(request, 'accounts/register.html', {'form': form})

class UserLoginView(View):
    def get(self, request):
        return render(request, 'accounts/login.html')

    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            
            # Store additional data in session
            request.session['user_id'] = user.id
            request.session['username'] = user.username
            if hasattr(user, 'profile') and user.profile.department:  # Check if Profile and department exist
                request.session['department'] = user.profile.department.name
            else:
                request.session['department'] = 'Unknown'

            # Redirect to dashboard
            return redirect('dashboard')
        
        # Handle invalid credentials
        messages.error(request, 'Invalid username or password.')
        return render(request, 'accounts/login.html')

class DocumentReceivedView(LoginRequiredMixin, View):
    def post(self, request, pk):
        # Retrieve the most recent DocumentStatus for the given document
        document_status = DocumentStatus.objects.filter(document__pk=pk).order_by('-timestamp').first()

        if document_status:
            # Ensure the document is in 'Forwarded' status and belongs to the current department
            if document_status.status == 'Forwarded' and document_status.department == request.user.profile.department:
                # Update the status to 'In Process'
                document_status.status = 'In Process'
                document_status.save()

                 # Check if a 'In Process' entry already exists in DocumentStatus
                if not DocumentStatus.objects.filter(document=document_status.document, status='In Process').exists():
                    # Create a new DocumentStatus entry only if 'In Process' doesn't exist
                    DocumentStatus.objects.create(
                        document=document_status.document,
                        status='In Process',
                        department=document_status.department
                    )

                # Get the latest status of the document
                latest_activity = DocumentActivity.objects.filter(document=document_status.document).order_by('-timestamp').first()

                # Create a DocumentActivity entry only if the latest activity doesn't match the current action
                if not latest_activity or latest_activity.action != 'Received':
                    DocumentActivity.objects.create(
                        document=document_status.document,  # Reference to the document
                        action='Received',  # Action taken by the user
                        performed_by=request.user  # Reference to the user who performed the action
                    )


                messages.success(request, 'Document marked as received and status updated to In Process.')
            else:
                messages.error(request, 'You are not authorized to receive this document or the document is not in Forwarded state.')
        else:
            messages.error(request, 'Document status not found.')

        return redirect('document_list')

class DocumentActivityView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
         # Fetch all activities
        query = request.GET.get('search', '')  # Get the search term from the query string
        all_activities = DocumentActivity.objects.select_related('document', 'performed_by').order_by('-timestamp')

        if query:  # If there's a search query, filter activities
            all_activities = all_activities.filter(
                Q(document__obligation_number__icontains=query) |
                Q(document__payee__icontains=query)
            )

        paginator = Paginator(all_activities, 10)  # Show 10 activities per page
        page_number = request.GET.get('page')  # Get the current page number from the query string
        page_obj = paginator.get_page(page_number)  # Get the corresponding page of activities

        context = {
            'activities': page_obj,  # Pass the paginated activities
            'query': query,
        }
        return render(request, 'document_activity.html', context)

    def get_document_activity_history(self, obligation_number):
        # Fetch the document by obligation_number
        document = get_object_or_404(Document, obligation_number=obligation_number)

        # Get all activities for this document, ordered by timestamp
        document_activity_history = DocumentActivity.objects.filter(document=document).order_by('-timestamp').values(
            'document__obligation_number', 'document__payee', 'action', 'performed_by__username', 'document__forwarded_to', 'timestamp')

        return document_activity_history

def document_activity_detail(request, obligation_number):
    # Fetch the document by obligation_number (as a string)
    document = get_object_or_404(Document, obligation_number=obligation_number)
    
    # Fetch all activities for this document
    activities = DocumentActivity.objects.filter(document=document).order_by('-timestamp')
    
    # Add pagination
    paginator = Paginator(activities, 10)  # 10 activities per page
    page_number = request.GET.get('page')  # Get the current page number from query parameters
    page_obj = paginator.get_page(page_number)  # Get the activities for the current page
    
    context = {
        'obligation_number': obligation_number,
        'activities': activities,
    }
    
    return render(request, 'document_activity_detail.html', context)
    
class DocumentDetailView(LoginRequiredMixin, DetailView):
    model = Document
    template_name = 'tracking/document_detail.html'
    context_object_name = 'document'

class DocumentSearchView(ListView):
    model = Document
    template_name = 'document_search.html'
    context_object_name = 'documents'
    paginate_by = 10  # Add pagination, if desired

    def get_queryset(self):
        # Get search and status filter parameters from the request
        query = self.request.GET.get('q', '')
        status_filter = self.request.GET.get('status', '')

        # Start with all documents
        queryset = Document.objects.all()

        # Apply search filter if there's a query
        if query:
            queryset = queryset.filter(Q(payee__icontains=query) | Q(description__icontains=query))

        # Apply status filter if a specific status is selected
        if status_filter:
            queryset = queryset.filter(document_status=status_filter)

        return queryset

    def get_context_data(self, **kwargs):
        # Pass the current search and status filter values to the template context
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['status_filter'] = self.request.GET.get('status', '')
        return context
    
class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'user_profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context

class DocumentHistoryView(ListView):
    model = DocumentActivity
    template_name = 'document_history.html'
    context_object_name = 'activities'

    def get_queryset(self):
        document_id = self.kwargs['pk']
        return DocumentActivity.objects.filter(document_id=document_id)

class DocumentUpdateStatusView(LoginRequiredMixin, View):
    def get(self, request, pk):
        try:
            document = get_object_or_404(Document, pk=pk)
            print(f"Document fetched: {document.payee} (ID: {document.pk})")

            # Fetch current document status for display purposes
            current_status = document.statuses.last()  # Get the latest status
            print(f"Current document status: {current_status.status if current_status else 'None'}")

            form = DocumentStatusUpdateForm(initial={
                'status': current_status.status if current_status else 'Pending',
                'department': document.forwarded_to if current_status and current_status.status == 'Forwarded' else None
            })

            # Determine if the "Receive" button should be shown based on status
            show_receive_button = current_status and current_status.status == "Returned" and document.initial_department == request.user.profile.department

            return render(request, 'tracking/document_update_status.html', {
                'document': document,
                'form': form,
                'show_receive_button': show_receive_button,  # Pass this flag to the template
            })
        
        except Exception as e:
            print(f"Error in GET request for document update: {str(e)}")
            messages.error(request, "An error occurred while fetching the document.")
            return redirect('document_list')

    def post(self, request, pk):
        try:
            document = get_object_or_404(Document, pk=pk)
            print(f"Document fetched for status update: {document.payee} (ID: {document.pk})")

            # Fetch current status of the document
            current_status = document.statuses.last()  # Get the latest status
            print(f"Current document status: {current_status.status if current_status else 'None'}")

            # Check if the document status is "Released" or "Returned"
            if current_status and current_status.status in ['Released', 'Returned']:
                # Allow updates only if the user is from the initial department
                if document.initial_department != request.user.profile.department:
                    messages.error(request, "You cannot update this document because it is either released or returned.")
                    return redirect('document_list')
                
            form = DocumentStatusUpdateForm(request.POST)

            if form.is_valid():
                status = form.cleaned_data['status']
                department = form.cleaned_data['department']

                print(f"Form is valid. Status: {status}, Department: {department}")

                 # Handle Returned status
                if status == 'Returned':
                    # Return the document to the initial department and set the status to Returned
                    document.forwarded_to = document.initial_department
                    document.save()
                    print(f"Document returned to initial department: {document.initial_department}")
                    
                # Create a new DocumentStatus entry
                document_status = DocumentStatus(
                    document=document,
                    status=status,
                    department=department or document.initial_department,  # Use the initial department if no forwarded department is selected
                )
                document_status.save()
                print(f"New DocumentStatus entry created with ID: {document_status.pk}")

                # Create a DocumentActivity entry to log this change
                activity = DocumentActivity(
                    document=document,
                    action=f"{status}",
                    performed_by=self.request.user,  # Log the user who made the change
                )
                activity.save()
                print(f"DocumentActivity entry created with ID: {activity.pk}")

                # Update the current_status field in Document model
                document.current_status = status  # Update the current status in the Document model
                document.save()
                print(f"Document current status updated to: {document.current_status}")

                # Update document status in Document model if necessary
                if status == 'Forwarded':
                    document.forwarded_to = department
                    document.save()
                    print(f"Document forwarded to department: {department}")

                messages.success(request, "Document status updated successfully.")
                return redirect('document_list')
            else:
                print(f"Form is invalid: {form.errors}")
                messages.error(request, "There was an error updating the status.")
            
            return render(request, 'tracking/document_update_status.html', {
                'document': document,
                'form': form,
            })
        
        except Exception as e:
            print(f"Error in POST request for document update: {str(e)}")
            messages.error(request, "An error occurred while updating the document status.")
            return render(request, 'tracking/document_update_status.html', {
                'document': document,
                'form': form,
            })
        
#Document Update for accounting
class UpdateDVFieldsView(LoginRequiredMixin, View):
    template_name = 'update_dv_fields.html'

    def get(self, request, pk, *args, **kwargs):
        # Log that the GET request was triggered
        print(f"GET request received for document ID: {pk}")

        # Get the document by ID
        document = get_object_or_404(Document, pk=pk)
        print(f"Document fetched: {document}")
        
        # Initialize default values for percentage fields
        percentage_fields = {
            'six_prcnt': Decimal('0.00'),
            'five_prcnt': Decimal('0.00'),
            'three_prcnt': Decimal('0.00'),
            'two_prcnt': Decimal('0.00'),
            'one_five_prcnt': Decimal('0.00'),
            'one_prcnt_frst': Decimal('0.00'),
            'one_prcnt_scnd': Decimal('0.00'),
        }

        # Update the percentage fields with actual document values if available
        for field, default_value in percentage_fields.items():
            if getattr(document, field, None) is not None:
                percentage_fields[field] = getattr(document, field)  # Use document value if available

        print(f"Initialized percentage fields with values: {percentage_fields}")

        # Create the form pre-populated with the document's current data
        form = AccountingForm(instance=document)
        print(f"Form initialized with document data: {form.initial}")

        # Define the percentage fields mapping
        percentages = {
            '6%': 'six_prcnt',
            '5%': 'five_prcnt',
            '3%': 'three_prcnt',
            '2%': 'two_prcnt',
            '1.5%': 'one_five_prcnt',
            '1% (First)': 'one_prcnt_frst',
            '1% (Second)': 'one_prcnt_scnd',
        }
        print(f"Percentages mapping: {percentages}")

        # Provide the form and document to the template
        context = {
            'form': form,
            'document': document,
            'percentages': percentages,
            'percentageData': percentage_fields,  # Add percentage fields with default or actual values
        }
        print("Context prepared for rendering.")
        return render(request, self.template_name, context)

    def post(self, request, pk, *args, **kwargs):
        print(f"POST request received for document ID: {pk}")

        # Fetch the document
        document = get_object_or_404(Document, pk=pk)
        print(f"Document fetched: {document}")

        # Loop through the percentage fields and update them if they are provided in the request
        percentage_fields = {
            'six_prcnt': Decimal('0.00'),
            'five_prcnt': Decimal('0.00'),
            'three_prcnt': Decimal('0.00'),
            'two_prcnt': Decimal('0.00'),
            'one_five_prcnt': Decimal('0.00'),
            'one_prcnt_frst': Decimal('0.00'),
            'one_prcnt_scnd': Decimal('0.00'),
        }
        
        # Create a form instance with POST data
        form = AccountingForm(request.POST, instance=document)
        print(f"Form data received: {request.POST}")

        if form.is_valid():
            print("Form is valid. Saving document...")
            form.save()
            print(f"Document updated with form data: {document}")

            # Process dynamically added percentage fields
            percentage_fields = [
                'six_prcnt', 'five_prcnt', 'three_prcnt', 'two_prcnt', 
                'one_five_prcnt', 'one_prcnt_frst', 'one_prcnt_scnd'
            ]

            # Loop through the percentage fields and ensure they are set correctly
            for field in percentage_fields:
                if field in request.POST and request.POST[field]:
                    # If the field is present in the POST data and has a value, update it
                    print(f"Updating field '{field}' with value: {request.POST[field]}")
                    # Ensure the value is a valid decimal
                    setattr(document, field, Decimal(request.POST[field]))
                else:
                    # If the field is missing in the POST data, set the default value (0.00)
                    print(f"Field '{field}' is missing in the request. Setting default value to Decimal('0.00').")
                    setattr(document, field, Decimal('0.00'))

            # Save the updated document with any percentage fields
            document.save()
            print("Document saved with updated percentage fields.")

            return redirect('document_list')
        else:
            print("Form is invalid. Errors:", form.errors)

        return render(request, self.template_name, {'form': form, 'document': document})

class CheckDocumentStatusUpdates(LoginRequiredMixin, View):
    def get(self, request):
        # Retrieve the department of the logged-in user
        user_department = request.user.profile.department  # Assuming a Profile model with department field linked to the user

        # Define the time range to get recent updates, e.g., last 10 minutes
        recent_time = timezone.now() - timedelta(minutes=10)

        # Filter DocumentStatus entries for the user's department with recent updates
        recent_status_updates = DocumentStatus.objects.filter(
            department=user_department,
            timestamp__gte=recent_time
        ).values('document_id', 'status', 'timestamp')

        # Convert queryset to list to return as JSON response
        return JsonResponse(list(recent_status_updates), safe=False)