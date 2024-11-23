from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from .forms import UserRegistrationForm
from django.views.generic import ListView, DetailView, TemplateView, UpdateView
from .models import Document, DocumentActivity, DocumentStatus, Department
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
from .forms import UserRegistrationForm, DocumentStatusUpdateForm  # Ensure this is your custom form with the department field
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.db import IntegrityError
from django.db import transaction


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

class UserLogoutView(LogoutView):
    next_page = reverse_lazy('login')  # Redirect to login page after logout

from django.contrib.auth.models import User
from .models import DocumentActivity

class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'tracking/document_form.html'
    success_url = reverse_lazy('document_list')

    def form_valid(self, form):
        print("Inside form_valid method")  # Debugging

        # Check if the form is valid
        if not form.is_valid():
            print(f"Form errors: {form.errors}")  # Debugging
            return self.form_invalid(form)
        else:
            print(f"Form errors: {form.errors}")
        
        # Retrieve the user's department
        user_department = getattr(self.request.user.profile, 'department', None)
        print(f"User's department retrieved: {user_department}")  # Debugging

        if not user_department:
            print("Error: No department found in user's profile.")  # Debugging
            messages.error(self.request, "Your profile does not have an assigned department.")
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                print("Starting transaction")  # Debugging

                # Attempt to save the document
                document = form.save(commit=False)
                document.initial_department = user_department
                document.status = 'In Process'
                print(f"Document before save: {document}")  # Debugging
                document.save()
                print(f"Document saved with ID: {document.id}")  # Debugging

                # Ensure that DocumentStatus is created only if the document was saved successfully
                if document.id:
                    DocumentStatus.objects.create(
                        document=document,
                        department=document.initial_department,
                        status=document.status
                    )
                    print("DocumentStatus entry created")  # Debugging
                    messages.success(self.request, "Document created and initial status recorded.")
                    
                    # Create DocumentActivity for the creation action
                    DocumentActivity.objects.create(
                        document=document,
                        action="Created",
                        performed_by=self.request.user,
                        timestamp=document.created_at  # Ensure the timestamp is correctly set
                    )
                    print("DocumentActivity entry created")

                else:
                    print("Error: Document save failed - No document ID.")  # Debugging
                    raise IntegrityError("Document save failed - No document ID.")

            # After successful save, render an empty form
            return redirect(self.success_url)

        except IntegrityError as e:
            print(f"IntegrityError occurred: {e}")  # Debugging
            messages.error(self.request, f"Error creating document: {str(e)}")
            return self.form_invalid(form)
        except Exception as ex:
            print(f"Unexpected error occurred: {ex}")  # Debugging
            messages.error(self.request, "An unexpected error occurred while creating the document.")
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        # Ensure the context includes the form for rendering
        context = super().get_context_data(**kwargs)
        context['form'] = DocumentForm()  # Provide a fresh form for the template
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
            timestamp=self.object.updated_at
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

        
class DocumentListView(ListView):
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
    def get(self, request, *args, **kwargs):
        # Step 1: Get the logged-in user's department
        user_department = request.user.profile.department  # Assuming the user has a profile with a department field

        # Step 2: Subquery to get the latest status timestamp for each department
        latest_department_statuses = DocumentStatus.objects.filter(
            department=user_department
        ).values('department').annotate(
            latest_status_timestamp=Max('timestamp')  # Get the latest timestamp per department
        )

        # Step 3: Filter DocumentStatus entries to get the latest status per department
        recent_statuses = DocumentStatus.objects.filter(
            department=user_department,  # Filter by the logged-in user's department
            timestamp__in=Subquery(latest_department_statuses.values('latest_status_timestamp'))
        )

        # Step 4: Initialize the status counts dictionary
        status_counts_dict = {
            'Pending': 0,
            'In_Process': 0,
            'Returned': 0,
            'Received': 0,
            'Forwarded': 0,
        }

        # Step 5: Count each status per department from the latest status entries
        for status in recent_statuses:
            status_name = status.status.replace(" ", "_")  # Replace spaces with underscores for consistency
            if status_name in status_counts_dict:
                status_counts_dict[status_name] += 1

        # Step 6: Retrieve recent activities for display (last 10 activities)
        recent_activities = DocumentActivity.objects.filter(
            document__in=Subquery(latest_department_statuses.values('document'))
        ).select_related('document', 'performed_by').order_by('-timestamp')[:10]  # Get the last 10 activities

        # Step 7: Prepare the context to pass to the template
        context = {
            'status_counts': status_counts_dict,  # Pass the status counts per department
            'recent_activities': recent_activities,  # Pass the recent activities
        }

        # Step 8: Render the dashboard template with the context data
        return render(request, 'dashboard.html', context)

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
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
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

                # Create a DocumentActivity entry only if it's not already created
                if not DocumentActivity.objects.filter(document=document_status.document, action='Received').exists():
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



class DocumentActivityView(View):
    def get(self, request):
        activities = DocumentActivity.objects.all().order_by('-timestamp')  # Assuming timestamp is a field in DocumentActivity
        return render(request, 'document_activity.html', {'activities': activities})
    
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
            queryset = queryset.filter(Q(title__icontains=query) | Q(description__icontains=query))

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

            return render(request, 'tracking/document_update_status.html', {
                'document': document,
                'form': form,
            })
        
        except Exception as e:
            print(f"Error in GET request for document update: {str(e)}")
            messages.error(request, "An error occurred while fetching the document.")
            return redirect('document_list')

    def post(self, request, pk):
        try:
            document = get_object_or_404(Document, pk=pk)
            print(f"Document fetched for status update: {document.payee} (ID: {document.pk})")

            form = DocumentStatusUpdateForm(request.POST)

            if form.is_valid():
                status = form.cleaned_data['status']
                department = form.cleaned_data['department']

                print(f"Form is valid. Status: {status}, Department: {department}")

                # Create a new DocumentStatus entry
                document_status = DocumentStatus(
                    document=document,
                    status=status,
                    department=department or document.initial_department,  # Use the initial department if no forwarded department is selected
                )
                document_status.save()
                print(f"New DocumentStatus entry created with ID: {document_status.pk}")

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