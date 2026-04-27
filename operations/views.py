from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from entity.models import Driver, Organization

def expense_by_autocomplete(request):
    term = request.GET.get("term", "")
    results = []

    drivers = Driver.objects.filter(first_name__icontains=term)[:10]
    for d in drivers:
        results.append({
            "id": f"driver_{d.id}",
            "text": f"Driver: {d.first_name} {d.last_name or ''}"
        })

    owners = Organization.objects.filter(
        organization_type__internal_value="OWNER",
        organization_name__icontains=term
    )[:10]
    for o in owners:
        results.append({
            "id": f"owner_{o.id}",
            "text": f"Owner: {o.organization_name}"
        })

    return JsonResponse({"results": results})
