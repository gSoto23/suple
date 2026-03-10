    let isCreating = false;

    const statusMap = {
        'created': 'Creado',
        'pending_payment': 'Pendiente de Pago',
        'paid': 'Pagado',
        'completed': 'Entregado',
        'cancelled': 'Cancelado',
        'refunded': 'Reembolsado'
    };

    document.addEventListener('DOMContentLoaded', async () => {
        await checkAuth();
        loadCustomers();
    });

    // ... (loadCustomers)

    async function loadCustomers() {
        const api = new ApiClient();
        try {
            const customers = await api.get('/customers/');
            const tbody = document.querySelector('#customers-table tbody');
            tbody.innerHTML = customers.map(c => `
                <tr>
                    <td><strong>${c.phone || '-'}</strong></td>
                    <td>${c.full_name}</td>
                    <td>
                        ${c.subscriptions && c.subscriptions.length > 0
                    ? c.subscriptions.map(s => `<span class="badge" style="background:var(--color-primary); color:white; margin-right:4px;">Sub #${s.id}</span>`).join('')
                    : '<span style="color: #999;">-</span>'
                }
                    </td>
                    <td>${c.email || '-'}</td>
                    <td>${c.address || '-'}</td>
                    <td>${c.default_payment_method || '-'}</td>
                    <td><span class="badge ${c.is_active ? 'active' : 'inactive'}">${c.is_active ? 'Activo' : 'Inactivo'}</span></td>
                    <td>
                        <button class="btn btn-sm btn-table-action" onclick="openCustomerModal('${c.phone}')">Ver</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteCustomer('${c.phone}', '${c.full_name}')" style="margin-left: 5px;"><i class="fa-solid fa-trash"></i></button>
                    </td>
                </tr>
            `).join('');
        } catch (e) {
            console.error(e);
        }
    }

    function closeCustomerModal() {
        document.getElementById('customer-modal').style.display = 'none';
    }

    function openCreateCustomerModal() {
        isCreating = true;
        document.getElementById('modal-title').innerText = 'Nuevo Cliente';
        document.getElementById('customer-form').reset();
        document.querySelector('[name="id"]').value = ''; // Still uses internal ID for update? Form uses ID? update logic needs checking.
        // Actually update also uses phone in API: PUT /customers/{phone}
        // But the form has input name="id".
        // Let's keep it consistent.

        document.getElementById('order-history-section').style.display = 'none'; // Hide history
        document.querySelector('#customer-modal .modal-content').style.maxWidth = '600px'; // Medium width

        // Set defaults
        const form = document.getElementById('customer-form');
        form.is_active.value = 'true';

        document.getElementById('customer-modal').style.display = 'flex';
    }

    async function openCustomerModal(phone) {
        if (!phone) {
            showToast('Error: Cliente sin teléfono', 'error');
            return;
        }
        isCreating = false;
        document.getElementById('modal-title').innerText = 'Detalle del Cliente';
        document.getElementById('order-history-section').style.display = 'block'; // Show history
        document.querySelector('#customer-modal .modal-content').style.maxWidth = '900px'; // Wide width

        const api = new ApiClient();
        try {
            // Fetch Customer Details
            const customer = await api.get(`/customers/${phone}`);

            // Fill Form
            const form = document.getElementById('customer-form');
            form.id.value = customer.id; // Internal ID might still be useful or we use phone as key
            form.full_name.value = customer.full_name;
            form.phone.value = customer.phone || '';
            form.email.value = customer.email || '';
            form.address.value = customer.address || '';
            form.is_active.value = (customer.is_active !== undefined ? customer.is_active : true).toString();
            form.default_payment_method.value = customer.default_payment_method || '';
            form.notes.value = customer.notes || '';

            form.age.value = customer.age || '';
            form.goal.value = customer.goal || '';
            form.training_days.value = customer.training_days || '';
            form.medical_data.value = customer.medical_data || '';

            // Store current customer Phone just in case
            document.getElementById('customer-modal').dataset.customerPhone = customer.phone;

            // Load Subscriptions in Modal Table
            renderCustomerSubscriptions(customer.subscriptions || []);

            // Fetch Order History
            loadCustomerOrders(customer.phone);

            document.getElementById('customer-modal').style.display = 'flex';
        } catch (e) {
            showToast('Error al cargar cliente', 'error');
            console.error(e);
        }
    }

    function renderCustomerSubscriptions(subs) {
        const tbody = document.querySelector('#customer-subscriptions-table tbody');
        if (!subs || subs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">No tiene suscripciones activas</td></tr>';
            return;
        }
        tbody.innerHTML = subs.map(s => `
            <tr>
                <td>#${s.id}</td>
                <td>P${s.product_id}</td>
                <td><span class="badge ${s.status}">${statusMap[s.status] || s.status}</span></td>
                <td>${s.next_billing_date ? formatDateCR(s.next_billing_date) : '-'}</td>
            </tr>
        `).join('');
    }

    async function loadCustomerOrders(phone) {
        const api = new ApiClient();
        const tbody = document.querySelector('#customer-orders-table tbody');
        tbody.innerHTML = '<tr><td colspan="5">Cargando...</td></tr>';

        try {
            const orders = await api.get(`/customers/${phone}/orders`);
            if (orders.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5">No hay ordenes registradas.</td></tr>';
                return;
            }
            tbody.innerHTML = orders.map(o => `
                    <tr>
                        <td>#${o.id}</td>
                        <td>${formatDateCR(o.created_at)}</td>
                        <td>${window.APP_CONFIG.currency} ${parseFloat(o.total_amount).toLocaleString()}</td>
                        <td><span class="badge ${o.status}">${statusMap[o.status] || o.status}</span></td>
                        <td>
                             <button class="btn btn-sm btn-table-action" onclick="openOrderModal(${o.id})">Ver</button>
                        </td>
                    </tr>
                `).join('');
        } catch (e) {
            console.error(e);
            tbody.innerHTML = '<tr><td colspan="5">Error al cargar ordenes.</td></tr>';
        }
    }

    async function openOrderModal(orderId) {
        const api = new ApiClient();
        try {
            const order = await api.get(`/orders/${orderId}`);

            // Populate Modal
            document.getElementById('modal-order-id').innerText = order.id;
            document.getElementById('modal-customer-name').innerText = order.customer ? order.customer.full_name : 'N/A';
            document.getElementById('modal-customer-phone').innerText = order.customer ? (order.customer.phone || 'N/A') : 'N/A';
            document.getElementById('modal-total').innerText = window.APP_CONFIG.currency + ' ' + parseFloat(order.total_amount).toLocaleString();

            // Status Select
            const statusSelect = document.getElementById('modal-status');
            statusSelect.innerHTML = Object.entries(statusMap).map(([key, label]) =>
                `<option value="${key}">${label}</option>`
            ).join('');
            statusSelect.value = order.status;

            // Populate Items
            const tbody = document.querySelector('#modal-items-table tbody');
            tbody.innerHTML = order.items.map(item => `
                    <tr>
                        <td>${item.product ? item.product.name : 'Unknown'}</td>
                        <td>${item.quantity}</td>
                        <td>${window.APP_CONFIG.currency} ${parseFloat(item.unit_price_at_moment).toLocaleString()}</td>
                        <td>${window.APP_CONFIG.currency} ${parseFloat(item.subtotal).toLocaleString()}</td>
                    </tr>
                `).join('');

            // Update footer total
            document.getElementById('modal-total').innerText = window.APP_CONFIG.currency + ' ' + parseFloat(order.total_amount).toLocaleString();

            document.getElementById('order-modal').style.zIndex = '1100';
            document.getElementById('order-modal').style.display = 'flex';
        } catch (e) {
            showToast('Error al cargar orden', 'error');
            console.error(e);
        }
    }

    function closeOrderModal() {
        document.getElementById('order-modal').style.display = 'none';
    }

    // ----------------------------------------------------
    // End Pet logic removed
    // ----------------------------------------------------

    // --- Subscriptions Logic ---
    function openCreateSubscriptionModal() {
        const customerId = document.getElementById('customer-form').id.value;
        if (!customerId) return;

        document.getElementById('subscription-form').reset();
        document.getElementById('sub-customer-id').value = customerId;

        // Default next billing date to today + 30
        const defaultDate = new Date();
        defaultDate.setDate(defaultDate.getDate() + 30);
        document.getElementById('sub-next-date').value = defaultDate.toISOString().split('T')[0];

        document.getElementById('subscription-modal').style.display = 'flex';
    }

    function closeSubscriptionModal() {
        document.getElementById('subscription-modal').style.display = 'none';
    }

    document.getElementById('subscription-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        const data = {
            customer_id: parseInt(document.getElementById('sub-customer-id').value),
            product_id: parseInt(document.getElementById('sub-product-id').value),
            frequency_days: parseInt(document.getElementById('sub-frequency').value),
            quantity: parseInt(document.getElementById('sub-quantity').value),
            status: "active",
            next_billing_date: new Date(document.getElementById('sub-next-date').value).toISOString(),
            notes: document.getElementById('sub-notes').value || null
        };

        const api = new ApiClient();
        try {
            await api.post('/subscriptions/', data);
            showToast('Suscripción creada correctamente', 'success');
            closeSubscriptionModal();

            // Reload Customer
            const currentPhone = document.getElementById('customer-modal').dataset.customerPhone;
            openCustomerModal(currentPhone);
        } catch (err) {
            showToast('Error al crear suscripción: ' + (err.detail || err.message), 'error');
        }
    });
    // ---------------------------

    document.getElementById('customer-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());

        // Convert 'true'/'false' string back to boolean for JSON
        data.is_active = data.is_active === 'true';

        try {
            const api = new ApiClient();
            if (isCreating) {
                delete data.id; // No ID for create
                await api.post('/customers/', data);
                showToast('Cliente creado correctamente', 'success');
            } else {
                // UPDATE: PUT /customers/{phone}
                const phone = data.phone;
                // We should use the original phone if it was changed? 
                // USUALLY update endpoint uses ID or original key.
                // If user changes phone, we effectively need the OLD phone to find it, OR update by ID?
                // API: PUT /customers/{phone} -> updates based on URL phone.
                // If user changed phone in form, data.phone is NEW phone.
                // We need OLD phone.
                // But wait, the API probably updates the record found by URL phone.
                // If we use data.phone (new phone), and it doesn't exist yet, we can't find record to update.
                // We need the ID or the original Phone.
                // But the API is keyed by phone.
                // If we change phone, we probably need to handle it carefully.
                // For now, let's assume we use the phone from form. 
                // If user edits phone, this might fail or create new?
                // Actually my `update_customer` uses `phone` in URL to find.
                // So we MUST use the phone that currently exists. 
                // If user edited the input, `data.phone` is new.
                // We should use `dataset.customerPhone` (original) for the URL.

                // Let's rely on dataset if available, or fetch from form if creating.
                // But if creating, isCreating is true.

                // For Update:
                const originalPhone = document.getElementById('customer-modal').dataset.customerPhone;
                // Use originalPhone for URL, and payload contains new phone.
                // The backend handles phone update check.

                delete data.id;
                await api.put(`/customers/${originalPhone}`, data);
                showToast('Cliente actualizado correctamente', 'success');

                // If phone changed, the next modal open needs new phone.
                // But we close modal anyway.
            }
            closeCustomerModal();
            loadCustomers();
        } catch (e) {
            showToast('Error: ' + (e.detail || e.message), 'error');
        }
    });

    async function deleteCustomer(phone, name) {
        showConfirm(
            'Eliminar Cliente',
            `¿Estás seguro de que deseas eliminar al cliente "${name}"? Esta acción no se puede deshacer.`,
            async () => {
                const api = new ApiClient();
                try {
                    await api.delete(`/customers/${phone}`);
                    showToast('Cliente eliminado correctamente', 'success');
                    loadCustomers();
                } catch (e) {
                    showToast('Error al eliminar: ' + (e.detail || e.message), 'error');
                }
            }
        );
    }
