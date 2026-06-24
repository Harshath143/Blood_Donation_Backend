# 🩸 LifeDrop Frontend API Integration Guide

This guide maps out all backend REST endpoints and WebSocket protocols exposed by the **LifeDrop API** at `/api/v1`.

## 🔒 Authentication & Headers

*   **Token Authentication**: Except for public authentication routes (`/api/v1/auth/...`), all endpoints require the `Authorization` header with a valid JWT access token:
    ```http
    Authorization: Bearer <access_token>
    ```
*   **Token Refresh Flow**: The access token expires in **15 minutes**. When expired, use the `refresh_token` (expires in 7 days) via `POST /api/v1/auth/refresh` to fetch a new pair of tokens.

---

## 🔑 1. Authentication Router (`/api/v1/auth`)

### 📝 User Registration
*   **Method & Path**: `POST /api/v1/auth/register`
*   **Rate Limit**: 10 requests per minute
*   **Payload (JSON)**:
    ```json
    {
      "email": "user@example.com",
      "phone": "+919876543210",
      "password": "Password@123",
      "full_name": "John Doe",
      "role": "donor" // Options: "donor", "hospital_admin", "user"
    }
    ```
    *Note: Password must be >=8 chars, containing uppercase, lowercase, number, and special character.*
*   **Response (201 Created)**:
    ```json
    {
      "id": "e4a5fdc8-10b2-4d2d-88b9-e1e79391ab6f",
      "email": "user@example.com",
      "phone": "+919876543210",
      "email_verified": false,
      "role": "donor",
      "full_name": "John Doe",
      "is_active": true,
      "created_at": "2026-06-24T09:30:00Z",
      "updated_at": "2026-06-24T09:30:00Z"
    }
    ```

### 🔓 User Login
*   **Method & Path**: `POST /api/v1/auth/login`
*   **Rate Limit**: 10 requests per minute
*   **Payload (JSON)**:
    ```json
    {
      "email": "user@example.com",
      "password": "Password@123"
    }
    ```
*   **Response (200 OK)**:
    ```json
    {
      "access_token": "eyJhbGciOi...",
      "refresh_token": "eyJhbGciOi...",
      "token_type": "bearer",
      "role": "donor",
      "full_name": "John Doe"
    }
    ```

### ✉️ Verify Email OTP
*   **Method & Path**: `POST /api/v1/auth/verify-otp`
*   **Payload (JSON)**:
    ```json
    {
      "email": "user@example.com",
      "otp": "123456"
    }
    ```
*   **Response (200 OK)**:
    ```json
    {
      "message": "Email verified successfully"
    }
    ```

### 🔁 Resend Verification OTP
*   **Method & Path**: `POST /api/v1/auth/resend-otp`
*   **Payload (JSON)**:
    ```json
    {
      "email": "user@example.com"
    }
    ```
*   **Response (200 OK)**:
    ```json
    {
      "message": "OTP sent successfully"
    }
    ```

### 🔄 Refresh Token Rotation
*   **Method & Path**: `POST /api/v1/auth/refresh`
*   **Payload (JSON)**:
    ```json
    {
      "refresh_token": "eyJhbGciOi..."
    }
    ```
*   **Response (200 OK)**:
    ```json
    {
      "access_token": "eyJhbGciOi...",
      "refresh_token": "eyJhbGciOi...",
      "token_type": "bearer",
      "role": "donor",
      "full_name": "John Doe"
    }
    ```

### 🔑 Forgot Password Request
*   **Method & Path**: `POST /api/v1/auth/forgot-password`
*   **Payload (JSON)**:
    ```json
    {
      "email": "user@example.com"
    }
    ```
*   **Response (200 OK)**:
    ```json
    {
      "message": "If the email is registered, a password reset code has been sent."
    }
    ```

### 🛠️ Reset Password
*   **Method & Path**: `POST /api/v1/auth/reset-password`
*   **Payload (JSON)**:
    ```json
    {
      "email": "user@example.com",
      "otp": "123456",
      "new_password": "NewSecurePassword@99"
    }
    ```
*   **Response (200 OK)**:
    ```json
    {
      "message": "Password reset successfully. You can now login with your new password."
    }
    ```

---

## 👤 2. User Router (`/api/v1/users`)

### 📋 Get Current Profile
*   **Method & Path**: `GET /api/v1/users/me`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Response (200 OK)**:
    ```json
    {
      "id": "e4a5fdc8-10b2-4d2d-88b9-e1e79391ab6f",
      "email": "user@example.com",
      "phone": "+919876543210",
      "email_verified": true,
      "role": "donor",
      "full_name": "John Doe",
      "is_active": true,
      "created_at": "2026-06-24T09:30:00Z",
      "updated_at": "2026-06-24T09:32:00Z"
    }
    ```

### ✏️ Update Current Profile
*   **Method & Path**: `PUT /api/v1/users/me`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Payload (JSON)**: All fields are optional:
    ```json
    {
      "full_name": "Johnathan Doe",
      "phone": "+919876543211",
      "email": "john.new@example.com"
    }
    ```
    *Note: Changing the email will reset `email_verified` to `false` and trigger another verification process.*
*   **Response (200 OK)**: Updated user object.

---

## 🩸 3. Donor Router (`/api/v1/donors`)

### 📋 Create / Update Donor Profile
*   **Method & Path**: `POST /api/v1/donors/profile`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Payload (JSON)**:
    ```json
    {
      "blood_type": "O+",
      "date_of_birth": "1995-10-15",
      "gender": "male",
      "weight_kg": 76.5,
      "address": "456 Park Avenue",
      "city": "Mumbai",
      "state": "Maharashtra",
      "pincode": "400001"
    }
    ```
*   **Response (200 OK)**:
    ```json
    {
      "id": "31b4025f-2b58-4796-9818-ee6693ff297d",
      "user_id": "e4a5fdc8-10b2-4d2d-88b9-e1e79391ab6f",
      "blood_type": "O+",
      "date_of_birth": "1995-10-15",
      "gender": "male",
      "weight_kg": 76.5,
      "city": "Mumbai",
      "state": "Maharashtra",
      "pincode": "400001",
      "latitude": 18.922,
      "longitude": 72.834,
      "availability": "always", // Options: "always", "weekends", "unavailable"
      "is_available_emergency": true,
      "last_donation_date": null,
      "total_donations": 0,
      "has_medical_conditions": false,
      "is_verified": true,
      "is_active": true,
      "created_at": "2026-06-24T09:35:00Z",
      "updated_at": "2026-06-24T09:35:00Z"
    }
    ```

### 🔍 Get My Donor Profile Details
*   **Method & Path**: `GET /api/v1/donors/me`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Response (200 OK)**: Returns the active donor profile object (schema matches above).

### ⚙️ Update Donor Availability
*   **Method & Path**: `PUT /api/v1/donors/availability`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Payload (JSON)**:
    ```json
    {
      "availability": "weekends", // Options: "always", "weekends", "unavailable"
      "is_available_emergency": false
    }
    ```
*   **Response (200 OK)**: Updated donor profile object.

---

## 🚨 4. Blood Request Router (`/api/v1/requests`)

### 🏥 Submit Blood Request (Supports Prescription File Upload)
*   **Method & Path**: `POST /api/v1/requests`
*   **Headers**: `Authorization: Bearer <access_token>`, Content-Type must be `multipart/form-data`.
*   **Payload (Form Data)**:
    | Key | Type | Description |
    | :--- | :--- | :--- |
    | `patient_name` | String (Required) | Name of the patient |
    | `patient_age` | Integer (Optional) | Age of the patient |
    | `blood_type_needed` | String (Required) | Compatible blood type (e.g. `A-`, `O+`) |
    | `units_needed` | Integer (Required) | Number of units requested |
    | `hospital_name` | String (Required) | Name of hospital where blood is required |
    | `hospital_address`| String (Required) | Location address of the hospital |
    | `city` | String (Required) | City name |
    | `state` | String (Required) | State name |
    | `required_by` | ISO Date String (Required) | Deadline (e.g., `2026-06-25T12:00:00Z`) |
    | `urgency_level` | String (Required) | `critical`, `urgent`, or `planned` |
    | `contact_name` | String (Required) | Point of contact name |
    | `contact_phone` | String (Required) | Point of contact phone |
    | `case_description` | String (Optional) | Details of the case / medical condition |
    | `prescription` | File (Optional) | Medical certificate or request slip upload |

*   **Response (200 OK)**:
    ```json
    {
      "id": "76495dbb-0c2d-456b-a25e-855ee038ef7a",
      "request_number": "REQ-1719221764",
      "requester_id": "e4a5fdc8-10b2-4d2d-88b9-e1e79391ab6f",
      "patient_name": "Jane Doe",
      "patient_age": 42,
      "blood_type_needed": "O+",
      "units_needed": 3,
      "hospital_id": null,
      "hospital_name": "City General Hospital",
      "city": "Mumbai",
      "state": "Maharashtra",
      "latitude": 18.922,
      "longitude": 72.834,
      "required_by": "2026-06-25T12:00:00Z",
      "urgency_level": "critical",
      "contact_name": "John Doe",
      "contact_phone": "+919876543210",
      "status": "matched", // Options: "pending", "matched", "no_match", "fulfilled", "cancelled"
      "prescription_oid": 16543,
      "prescription_name": "cert.pdf",
      "prescription_mime": "application/pdf",
      "case_description": "Scheduled open-heart surgery.",
      "matched_at": "2026-06-24T09:40:00Z",
      "fulfilled_at": null,
      "cancelled_at": null,
      "cancellation_reason": null,
      "broadcast_radius_km": 25,
      "donors_notified": 8,
      "created_at": "2026-06-24T09:36:00Z",
      "updated_at": "2026-06-24T09:40:00Z"
    }
    ```

### 📋 List & Filter Blood Requests
*   **Method & Path**: `GET /api/v1/requests`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Query Parameters (Optional)**:
    *   `status`: Filter by status (e.g. `matched`, `pending`, `fulfilled`, `cancelled`)
    *   `blood_type`: Filter by requested blood type (e.g. `B+`)
    *   `city`: Filter by city name (fuzzy search)
    *   `my_requests`: Boolean (`true` to show requests made by the current user)
*   **Response (200 OK)**: List of blood request objects.

### 🔍 Get Request Details
*   **Method & Path**: `GET /api/v1/requests/{request_id}`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Response (200 OK)**: Single request object matching the details schema.

### 📥 Download Prescription Document
*   **Method & Path**: `GET /api/v1/requests/{request_id}/prescription`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Response**: Binary stream download of the uploaded document (PDF/Image).

### 🛑 Cancel Blood Request
*   **Method & Path**: `PUT /api/v1/requests/{request_id}/cancel`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Payload (JSON)**:
    ```json
    {
      "cancellation_reason": "Patient received blood from local inventory."
    }
    ```
*   **Response (200 OK)**: Cancelled request object with status update.

### ✅ Fulfill Blood Request
*   **Method & Path**: `PUT /api/v1/requests/{request_id}/fulfill`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Payload (JSON)**: None
*   **Response (200 OK)**: Request object updated with `status = "fulfilled"` and `fulfilled_at` set.

### 🤝 Get Request Notification Matches (Admins, Owner, or Notified Donor)
*   **Method & Path**: `GET /api/v1/requests/{request_id}/matches`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Response (200 OK)**:
    ```json
    [
      {
        "id": "d09b67ff-7c3e-4fb6-af7f-be9d5248107d",
        "request_id": "76495dbb-0c2d-456b-a25e-855ee038ef7a",
        "donor_id": "31b4025f-2b58-4796-9818-ee6693ff297d",
        "status": "pending", // Options: "pending", "accepted", "rejected", "donated"
        "distance_km": 12.45,
        "compatibility": "exact",
        "notified_at": "2026-06-24T09:40:00Z",
        "responded_at": null,
        "donated_at": null,
        "rejection_reason": null
      }
    ]
    ```

### 🙋 Respond to Match Alert (Accept / Reject)
*   **Method & Path**: `POST /api/v1/requests/{request_id}/matches/respond`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Payload (JSON)**:
    ```json
    {
      "status": "accepted", // Options: "accepted", "rejected"
      "rejection_reason": null // Provide string if rejected, otherwise null
    }
    ```
*   **Response (200 OK)**: Updated Match status object.

---

## 💉 5. Donations Router (`/api/v1/donations`)

### 📋 Record a Blood Donation
*   **Method & Path**: `POST /api/v1/donations`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Payload (JSON)**:
    ```json
    {
      "donor_id": null, // Specify donor UUID if admin recording for others. Null for self.
      "request_id": "76495dbb-0c2d-456b-a25e-855ee038ef7a", // Optional
      "blood_bank_id": null, // Optional
      "blood_type": "O+",
      "units_donated": 1.0,
      "donation_type": "whole_blood", // "whole_blood", "platelets", "plasma"
      "donated_at": "2026-06-24T08:00:00Z",
      "location_name": "City General Hospital",
      "certificate_number": "CERT-8877665" // Optional certificate id (unique)
    }
    ```
*   **Response (201 Created)**:
    ```json
    {
      "id": "c1f77d33-90be-4a2a-88cb-ff0923ab6711",
      "donor_id": "31b4025f-2b58-4796-9818-ee6693ff297d",
      "request_id": "76495dbb-0c2d-456b-a25e-855ee038ef7a",
      "blood_bank_id": null,
      "blood_type": "O+",
      "units_donated": 1.0,
      "donation_type": "whole_blood",
      "donated_at": "2026-06-24T08:00:00Z",
      "location_name": "City General Hospital",
      "certificate_number": "CERT-8877665",
      "created_at": "2026-06-24T09:45:00Z"
    }
    ```

### 📜 Get My Donation History
*   **Method & Path**: `GET /api/v1/donations/me`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Response (200 OK)**: List of donation records created by this donor.

### 🔑 Get specific Donor History (Admins / Staff Only)
*   **Method & Path**: `GET /api/v1/donations/donor/{donor_id}`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Response (200 OK)**: List of donation records for the target donor.

---

## 🏦 6. Blood Bank Router (`/api/v1/blood-banks`)

### 📝 Create a Blood Bank (Super Admin Only)
*   **Method & Path**: `POST /api/v1/blood-banks`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Payload (JSON)**:
    ```json
    {
      "name": "Red Cross Central Bank",
      "hospital_id": null, // Associated Hospital UUID if any
      "address": "12 Arterial Road",
      "city": "Mumbai",
      "state": "Maharashtra",
      "pincode": "400002",
      "phone": "+912225432101",
      "email": "mumbaicentral@redcross.org",
      "operating_hours": {
        "weekday": "09:00 - 18:00",
        "weekend": "10:00 - 15:00"
      },
      "is_24x7": false
    }
    ```
*   **Response (201 Created)**: Created blood bank object including geocoded latitude/longitude coordinates.

### 🔍 List and Filter Blood Banks
*   **Method & Path**: `GET /api/v1/blood-banks`
*   **Query Parameters (Optional)**:
    *   `city`: Filter by city name (fuzzy matching, e.g., `Mumbai`)
    *   `state`: Filter by state name
*   **Response (200 OK)**: Array of available active blood bank locations.

### 🏥 Get Inventory Levels
*   **Method & Path**: `GET /api/v1/blood-banks/{blood_bank_id}/inventory`
*   **Response (200 OK)**:
    ```json
    [
      {
        "id": "e43b123d-c112-4cf4-912f-ee87611ab998",
        "blood_bank_id": "f5127022-de9a-4122-81de-ef9900ab12cf",
        "blood_type": "O+",
        "units_available": 45,
        "units_reserved": 5,
        "last_updated": "2026-06-24T09:00:00Z"
      }
    ]
    ```

### ⚙️ Update Inventory Levels (Admin / Hospital Staff)
*   **Method & Path**: `POST /api/v1/blood-banks/{blood_bank_id}/inventory`
*   **Payload (JSON)**:
    ```json
    {
      "blood_type": "O+",
      "units": 10 // Can be positive to add stock, or negative to deduct stock
    }
    ```
*   **Response (200 OK)**: Updated inventory line item.

---

## ⚡ 7. Real-Time WebSockets (`ws://`)

Connect dynamically to the real-time events manager to receive push alerts.

*   **Connection URL**: `ws://<backend_domain>/api/v1/ws?token=<JWT_ACCESS_TOKEN>`

### 📤 Outbound Client Messages
Send a heartbeat connection ping:
```json
{
  "event": "ping"
}
```
*Response*:
```json
{
  "event": "pong"
}
```

### 📥 Inbound Server Messages (Push Events)

#### 1. Match Notification (`match_found`)
Triggered to the **requester** when the system successfully finds matching donors nearby.
```json
{
  "event": "match_found",
  "request_id": "76495dbb-0c2d-456b-a25e-855ee038ef7a",
  "donors_notified": 8,
  "search_radius_km": 25
}
```

#### 2. Donor Accepts Match (`match_accepted`)
Triggered to the **requester** when a donor accepts the matching request notification alert.
```json
{
  "event": "match_accepted",
  "request_id": "76495dbb-0c2d-456b-a25e-855ee038ef7a",
  "donor_name": "John Doe",
  "donor_phone": "+919876543210" // Revealed only when accepted
}
```

#### 3. Donor Declines Match (`match_declined`)
Triggered to the **requester** when a donor declines the match alert.
```json
{
  "event": "match_declined",
  "request_id": "76495dbb-0c2d-456b-a25e-855ee038ef7a",
  "donor_name": "John Doe",
  "donor_phone": null
}
```
