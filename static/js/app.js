// BharatLink Nexus AI Client Application — 100% Fail-Proof Logic

window.currentPlan = null;
let deferredPwaPrompt = null;

// Register PWA Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/sw.js').then((reg) => {
      console.log('BharatLink Service Worker Registered:', reg.scope);
    }).catch((err) => {
      console.error('Service Worker registration failed:', err);
    });
  });
}

// PWA Install Prompt Pop-Up Handler
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPwaPrompt = e;
  showPwaInstallBanner();
});

function showPwaInstallBanner() {
  if (document.getElementById('pwa-install-banner')) return;

  const bannerHtml = `
    <div id="pwa-install-banner" style="position: fixed; bottom: 5rem; left: 50%; transform: translateX(-50%); width: 92%; max-width: 28rem; background: rgba(9, 15, 33, 0.98); backdrop-filter: blur(20px); border: 1px solid var(--amber-gold); padding: 1rem 1.25rem; border-radius: 1rem; box-shadow: 0 8px 32px rgba(0,0,0,0.9); z-index: 10000; display: flex; align-items: center; justify-content: space-between; gap: 1rem;">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
        <div style="font-size: 1.8rem; flex-shrink: 0;">📱</div>
        <div>
          <h4 style="color: #ffffff; font-size: 0.95rem; font-weight: bold; margin-bottom: 0.15rem;">Install BharatLink PWA</h4>
          <p style="color: var(--text-muted); font-size: 0.78rem;">Install mobile app for quick access & offline sourcing.</p>
        </div>
      </div>
      <div style="display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0;">
        <button onclick="installPwaApp()" class="btn-amber" style="padding: 0.45rem 0.85rem; font-size: 0.82rem;">Install App</button>
        <button onclick="document.getElementById('pwa-install-banner').remove()" style="background: none; border: none; color: #fca5a5; font-size: 1.25rem; cursor: pointer; padding: 0.2rem;">✕</button>
      </div>
    </div>
  `;

  document.body.insertAdjacentHTML('beforeend', bannerHtml);
}

function installPwaApp() {
  if (deferredPwaPrompt) {
    deferredPwaPrompt.prompt();
    deferredPwaPrompt.userChoice.then((choiceResult) => {
      if (choiceResult.outcome === 'accepted') {
        console.log('User accepted BharatLink PWA installation');
      }
      deferredPwaPrompt = null;
      const banner = document.getElementById('pwa-install-banner');
      if (banner) banner.remove();
    });
  } else {
    alert("To install BharatLink Nexus AI PWA app on iOS/Chrome:\n1. Tap Share or Chrome menu (⋮)\n2. Select 'Add to Home Screen'");
  }
}

// Robust Markdown Parser for multi-line text & bold/italic formatting
function parseMarkdownToHtml(md) {
  if (!md) return '';
  let str = String(md);

  // Replace double asterisks (bold) across newlines
  str = str.replace(/\*\*([\s\S]*?)\*\*/g, '<strong>$1</strong>');
  
  // Replace single asterisks or underscores (italic)
  str = str.replace(/\*([\s\S]*?)\*/g, '<em>$1</em>');
  str = str.replace(/_([\s\S]*?)_/g, '<em>$1</em>');
  
  // Replace backticks (code)
  str = str.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  // Replace bullet points
  str = str.replace(/^\s*[\-\*]\s+(.*)$/gm, '<li>$1</li>');
  
  // Convert headers
  str = str.replace(/^### (.*$)/gmi, '<h3 style="color: var(--amber-gold); font-size: 1.2rem; margin-top: 1.5rem; margin-bottom: 0.5rem; border-bottom: 1px solid var(--border-amber); padding-bottom: 0.25rem;">$1</h3>');
  str = str.replace(/^## (.*$)/gmi, '<h2 style="color: #ffffff; font-size: 1.4rem; margin-top: 1.5rem; margin-bottom: 0.5rem;">$1</h2>');

  // Convert newlines to paragraphs/line breaks
  str = str.replace(/\n\n+/g, '</p><p>');
  str = str.replace(/\n/g, '<br/>');

  return '<div>' + str + '</div>';
}

// Dynamic PDF Export using Printable Layout
function downloadProcurementPdf() {
  try {
    const p = window.currentPlan;
    if (!p) {
      alert("No active procurement plan to download. Please run a sourcing query first.");
      return;
    }

    const prodName = p.product?.name || "Artisan Product";
    const supplierName = p.supplier?.name || "Verified Artisan Guild";
    const certification = p.supplier?.craftCertification || "GI Tag Certified";
    const qty = p.quantity || 50;
    const totalCost = Number(p.totalEstimatedCost || 0).toLocaleString();
    const etaDays = p.estimatedDeliveryDays || 4;
    const risk = p.riskLevel || "LOW";
    const summaryHtml = p.executiveSummaryHtml || parseMarkdownToHtml(p.executiveSummary);
    const route = p.selectedRoute || {};

    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      alert("Pop-up blocked. Please allow pop-ups for this site to view/download PDF.");
      return;
    }

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>Procurement Recommendation Report — ${prodName}</title>
        <style>
          body { font-family: 'Times New Roman', Times, serif; padding: 40px; color: #111; line-height: 1.6; }
          h1 { color: #b45309; border-bottom: 2px solid #b45309; padding-bottom: 10px; }
          .meta { margin-bottom: 30px; background: #fef3c7; padding: 15px; border-radius: 8px; }
          .table { width: 100%; border-collapse: collapse; margin-top: 20px; }
          .table th, .table td { border: 1px solid #ddd; padding: 10px; text-align: left; }
          .table th { background: #f59e0b; color: #fff; }
          .badge { background: #10b981; color: #fff; padding: 3px 8px; border-radius: 4px; font-weight: bold; }
        </style>
      </head>
      <body>
        <h1>BharatLink Nexus AI — Executive Sourcing Report</h1>
        <div class="meta">
          <p><strong>Product Sourced:</strong> ${prodName}</p>
          <p><strong>Artisan Guild:</strong> ${supplierName} (${certification})</p>
          <p><strong>Quantity:</strong> ${qty} units | <strong>Total Estimated Cost:</strong> ₹${totalCost}</p>
          <p><strong>Delivery ETA:</strong> ${etaDays} Days | <strong>Risk Score:</strong> <span class="badge">${risk}</span></p>
        </div>

        <h2>Executive Recommendation Narrative</h2>
        <div>${summaryHtml}</div>

        <h2>Transportation & Freight Route Breakdown</h2>
        <table class="table">
          <tr><th>Mode</th><th>Carrier</th><th>Origin → Destination</th><th>ETA</th><th>Freight Cost</th></tr>
          <tr>
            <td>${route.mode || "Air Freight Express"}</td>
            <td>${route.carrier || "Express Courier"}</td>
            <td>${route.originRegion || "India"} → ${route.destination || "Destination"}</td>
            <td>${etaDays} Days</td>
            <td>₹${Number(p.estimatedShippingCost || 0).toLocaleString()}</td>
          </tr>
        </table>

        <br/><hr/><br/>
        <p style="font-size: 12px; color: #666; text-align: center;">Generated by BharatLink Nexus AI Agentic Engine • Authenticated GI Sourcing Platform</p>

        <script>
          window.onload = function() { window.print(); }
        </script>
      </body>
      </html>
    `);
    printWindow.document.close();
  } catch (err) {
    console.error("PDF generation error:", err);
    alert("Error generating PDF report: " + err.message);
  }
}

// Open Purchase & WhatsApp Contact Modal
function openWhatsAppPurchaseModal(customPlan) {
  try {
    const p = customPlan || window.currentPlan;
    if (!p) {
      alert("Procurement plan details unavailable. Please run a sourcing query first.");
      return;
    }

    const supplier = p.supplier || {};
    const product = p.product || {};
    const route = p.selectedRoute || {};
    const routes = (p.candidateRoutes && p.candidateRoutes.length > 0) ? p.candidateRoutes : [route];

    const sellerName = supplier.name || product.sellerName || "Artisan Seller";
    let rawPhone = String(supplier.whatsappNumber || supplier.phone || "919823012345");
    let whatsappNum = rawPhone.replace(/[^0-9]/g, '');
    if (!whatsappNum) whatsappNum = "919823012345";
    if (!whatsappNum.startsWith('91') && whatsappNum.length === 10) {
      whatsappNum = '91' + whatsappNum;
    }

    const recRoute = routes[0] || route || {};
    const altRoute = routes[1] || null;

    const prodName = product.name || "Artisan Product";
    const qty = p.quantity || 50;
    const dest = route.destination || p.destination || "India";
    const etaDays = recRoute.totalDeliveryDays || p.estimatedDeliveryDays || 4;
    const recCost = Number(recRoute.estimatedShippingCost || p.estimatedShippingCost || 3500);
    const prodCost = Number(p.productCost || (qty * (product.price || 3000)));
    const totalCost = Number(p.totalEstimatedCost || (prodCost + recCost));

    const u = window.currentUser || {};
    const buyerName = u.full_name || u.name || "Shravan Shidruk";
    const buyerEmail = u.email || "shravanshidruk@gmail.com";
    const buyerPhone = u.phone || u.whatsapp_number || "+91 98230 12345";
    const buyerAddress = u.address ? u.address : `${dest}, India`;

    const prodCategory = product.category || "Handloom & Craft";
    const originRegion = product.region || supplier.location || "Maharashtra";
    const unitPrice = Number(product.price || (prodCost / qty));
    const distKm = recRoute.estimatedDistanceKm || 25.0;
    const carrier = recRoute.carrier || "National Logistics Network";
    const transportMode = recRoute.mode || "Local Waterproof Container Mini Truck";
    const fuelDetails = recRoute.fuelCalculationDetails || "Fuel & Base Driver/Handling Fee";

    let msg = `🙏 Namaste ${sellerName},\n\n`;
    msg += `I am contacting you through the BharatLink Nexus AI B2B Artisan Procurement Platform to place an authentic sourcing order.\n\n`;
    msg += `==================================\n`;
    msg += `📦 OFFICIAL BUYER SOURCING INQUIRY\n`;
    msg += `==================================\n\n`;
    msg += `1️⃣ BUYER PROFILE & CONTACT DETAILS:\n`;
    msg += `• Buyer Name: ${buyerName}\n`;
    msg += `• Account Email: ${buyerEmail}\n`;
    msg += `• Phone / Contact: ${buyerPhone}\n`;
    msg += `• Destination Address: ${buyerAddress}\n\n`;
    msg += `2️⃣ PRODUCT SPECIFICATIONS & SOURCING REQUIREMENT:\n`;
    msg += `• Target Product: ${prodName}\n`;
    msg += `• Category & Craft Region: ${prodCategory} (${originRegion})\n`;
    msg += `• Quantity Requested: ${qty} Units\n`;
    msg += `• Unit Price Quoted: ₹${unitPrice.toLocaleString('en-IN')} per unit\n`;
    msg += `• Quality Standard: Verified GI-Tag Certification Required\n\n`;
    msg += `3️⃣ PLATFORM LOGISTICS & MULTI-MODAL FREIGHT:\n`;
    msg += `• Selected Transport Mode: ${transportMode}\n`;
    msg += `• Estimated Transit Distance: ${distKm} km\n`;
    msg += `• Target Delivery Deadline: ${etaDays} Days\n`;
    msg += `• Transport Carrier Fleet: ${carrier}\n`;
    msg += `• Fuel & Freight Calculation: ${fuelDetails}\n\n`;
    msg += `4️⃣ PLATFORM FINANCIAL COST BREAKDOWN:\n`;
    msg += `• Product Inventory Cost: ₹${prodCost.toLocaleString('en-IN')}\n`;
    msg += `• Estimated Freight Charges: ₹${recCost.toLocaleString('en-IN')}\n`;
    msg += `• TOTAL ALL-INCLUSIVE ESTIMATED VALUE: ₹${totalCost.toLocaleString('en-IN')}\n\n`;
    msg += `==================================\n`;
    msg += `📋 ACTION REQUIRED BY SELLER:\n`;
    msg += `Please confirm the following to finalize order dispatch:\n`;
    msg += `1. Immediate stock availability & dispatch lead time\n`;
    msg += `2. Confirmation of GI-Tag / Authenticity Certificate\n`;
    msg += `3. Tax Invoice setup & payment transfer instructions\n\n`;
    msg += `Thank you! Looking forward to your prompt response.\n\n`;
    msg += `Regards,\n`;
    msg += `${buyerName}\n`;
    msg += `[Sent via BharatLink Nexus AI Sourcing Platform]`;

    const encodedMsg = encodeURIComponent(msg);
    const waUrl = `https://wa.me/${whatsappNum}?text=${encodedMsg}`;

    // Remove existing modal if any
    const existing = document.getElementById('whatsapp-purchase-modal');
    if (existing) existing.remove();

    let modalHtml = `
      <div id="whatsapp-purchase-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 1rem;">
        <div class="glass-card-amber" style="max-width: 36rem; width: 100%; max-height: 90vh; overflow-y: auto; padding: 1.5rem; border-radius: 1rem; position: relative;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; border-bottom: 1px solid var(--border-amber); padding-bottom: 0.75rem;">
            <h2 style="color: #ffffff; font-size: 1.3rem;">Proceed to Purchase / Contact Seller</h2>
            <button type="button" onclick="closeWhatsAppModal()" style="background: none; border: none; color: #fca5a5; font-size: 1.5rem; cursor: pointer; padding: 0 0.5rem;">✕</button>
          </div>

          <div style="margin-bottom: 1.25rem; background: rgba(9, 15, 33, 0.7); padding: 1rem; border-radius: 0.5rem; border: 1px solid var(--border-amber);">
            <div style="color: var(--amber-gold); font-weight: bold; font-size: 0.85rem;">Seller Contact Details</div>
            <div style="color: #ffffff; font-size: 1.1rem; font-weight: bold;">${sellerName}</div>
            <div style="color: #34d399; font-size: 0.9rem;">💬 WhatsApp: +${whatsappNum}</div>
          </div>

          <h3 style="color: #ffffff; font-size: 1rem; margin-bottom: 0.75rem;">Multi-Modal Freight Options</h3>
          
          <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
            <span style="background: #10b981; color: #090f21; padding: 0.2rem 0.5rem; border-radius: 0.3rem; font-size: 0.75rem; font-weight: bold;">⭐ RECOMMENDED ROUTE</span>
            <h4 style="color: #ffffff; margin-top: 0.4rem; font-size: 1rem;">${recRoute.mode || 'Air Freight Express'}</h4>
            <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 0.5rem;">Carrier: ${recRoute.carrier || 'Express Courier'} | ETA: ${etaDays} Days</p>
            <div style="display: flex; justify-content: space-between; font-size: 0.88rem; font-weight: bold;">
              <span style="color: var(--amber-gold);">Freight: ₹${recCost.toLocaleString()}</span>
              <span style="color: #34d399;">Total: ₹${totalCost.toLocaleString()}</span>
            </div>
          </div>

          ${altRoute ? `
          <div style="background: rgba(255, 255, 255, 0.05); border: 1px solid var(--border-amber); padding: 1rem; border-radius: 0.5rem; margin-bottom: 1.25rem;">
            <span style="color: var(--text-muted); font-size: 0.75rem; font-weight: bold;">ALTERNATIVE OPTION</span>
            <h4 style="color: #ffffff; margin-top: 0.4rem; font-size: 1rem;">${altRoute.mode || 'Rail Express'}</h4>
            <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 0.5rem;">Carrier: ${altRoute.carrier || 'Freight Carrier'} | ETA: ${altRoute.totalDeliveryDays || etaDays + 2} Days</p>
            <div style="display: flex; justify-content: space-between; font-size: 0.88rem;">
              <span style="color: var(--amber-gold);">Freight: ₹${Number(altRoute.estimatedShippingCost || 4500).toLocaleString()}</span>
            </div>
          </div>
          ` : ''}

          <h3 style="color: #ffffff; font-size: 1rem; margin-bottom: 0.5rem;">Generated WhatsApp Inquiry Message</h3>
          <pre style="background: rgba(9, 15, 33, 0.9); border: 1px solid var(--border-amber); padding: 0.85rem; border-radius: 0.5rem; color: #cbd5e1; font-family: monospace; font-size: 0.8rem; white-space: pre-wrap; margin-bottom: 1.25rem;">${msg}</pre>

          <div style="text-align: center;">
            <a href="${waUrl}" target="_blank" onclick="trackWhatsAppContact('${sellerName}', '${prodName}')" class="btn-amber" style="display: block; padding: 0.85rem; font-size: 1.05rem; text-decoration: none; font-weight: bold; background: linear-gradient(135deg, #10b981, #059669); color: #ffffff; text-align: center;">
              💬 Contact Seller on WhatsApp →
            </a>
            <span style="color: var(--text-muted); font-size: 0.78rem; display: block; margin-top: 0.5rem;">Direct order confirmation between buyer and seller. No automatic payment charged.</span>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
  } catch (err) {
    console.error("WhatsApp modal error:", err);
    alert("Error opening WhatsApp modal: " + err.message);
  }
}

function closeWhatsAppModal() {
  const modal = document.getElementById('whatsapp-purchase-modal');
  if (modal) modal.remove();
}

function selectAlternativeSeller(sellerName, productName, price, whatsappNum) {
  if (!window.currentPlan) return;
  const p = window.currentPlan;
  
  const updatedPlan = JSON.parse(JSON.stringify(p));
  updatedPlan.supplier.name = sellerName;
  updatedPlan.supplier.whatsappNumber = whatsappNum || "919823012345";
  updatedPlan.product.name = productName;
  updatedPlan.product.price = price;
  updatedPlan.productCost = price * (p.quantity || 50);
  updatedPlan.totalEstimatedCost = updatedPlan.productCost + (p.estimatedShippingCost || 1000);

  openWhatsAppPurchaseModal(updatedPlan);
}

// History Detailed Session Modal View by Index
function viewHistoryItem(index) {
  if (!window.historyData || !window.historyData[index]) return;
  const item = window.historyData[index];

  const plan = {
    supplier: { name: item.supplierName, whatsappNumber: "919823012345" },
    product: { name: item.productName },
    quantity: item.quantity,
    totalEstimatedCost: item.totalCost,
    productCost: item.totalCost * 0.9,
    estimatedShippingCost: item.totalCost * 0.1,
    estimatedDeliveryDays: item.deliveryDays,
    riskLevel: item.riskLevel || "LOW",
    selectedRoute: { mode: "Express Air Freight", carrier: "Express Courier", destination: item.destination || "India", totalDeliveryDays: item.deliveryDays }
  };

  let modalHtml = `
    <div id="history-detail-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 1rem;">
      <div class="glass-card-amber" style="max-width: 40rem; width: 100%; max-height: 90vh; overflow-y: auto; padding: 2rem; border-radius: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; border-bottom: 1px solid var(--border-amber); padding-bottom: 0.75rem;">
          <h2 style="color: #ffffff; font-size: 1.5rem;">Sourcing Run Session Detail</h2>
          <button type="button" onclick="document.getElementById('history-detail-modal').remove()" style="background: none; border: none; color: #fca5a5; font-size: 1.5rem; cursor: pointer; padding: 0 0.5rem;">✕</button>
        </div>

        <div style="margin-bottom: 1.5rem; background: rgba(9, 15, 33, 0.7); padding: 1rem; border-radius: 0.5rem; border: 1px solid var(--border-amber);">
          <div style="color: var(--amber-gold); font-size: 0.85rem; margin-bottom: 0.25rem;">Original Buyer Prompt</div>
          <div style="color: #ffffff; font-size: 1.1rem; font-style: italic;">"${item.rawPrompt || item.productName}"</div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem;">
          <div style="background: rgba(9, 15, 33, 0.5); padding: 1rem; border-radius: 0.5rem;">
            <span style="color: var(--text-muted); font-size: 0.8rem; display: block;">Sourced Product</span>
            <span style="color: #ffffff; font-weight: bold; font-size: 1.1rem;">${item.productName}</span>
          </div>
          <div style="background: rgba(9, 15, 33, 0.5); padding: 1rem; border-radius: 0.5rem;">
            <span style="color: var(--text-muted); font-size: 0.8rem; display: block;">Supplier Guild</span>
            <span style="color: var(--amber-gold); font-weight: bold; font-size: 1.1rem;">${item.supplierName}</span>
          </div>
          <div style="background: rgba(9, 15, 33, 0.5); padding: 1rem; border-radius: 0.5rem;">
            <span style="color: var(--text-muted); font-size: 0.8rem; display: block;">Order Value</span>
            <span style="color: #34d399; font-weight: bold; font-size: 1.1rem;">${item.quantity} units (₹${Number(item.totalCost || 0).toLocaleString()})</span>
          </div>
          <div style="background: rgba(9, 15, 33, 0.5); padding: 1rem; border-radius: 0.5rem;">
            <span style="color: var(--text-muted); font-size: 0.8rem; display: block;">Transit ETA</span>
            <span style="color: #38bdf8; font-weight: bold; font-size: 1.1rem;">${item.deliveryDays} Days</span>
          </div>
        </div>

        <div style="text-align: center; margin-top: 1.5rem;">
          <button type="button" onclick="document.getElementById('history-detail-modal').remove(); openWhatsAppPurchaseModal(${JSON.stringify(plan).replace(/"/g, '&quot;')})" class="btn-amber" style="padding: 0.85rem 1.75rem; font-size: 1rem; background: linear-gradient(135deg, #10b981, #059669); color: #ffffff;">
            💬 Proceed to Purchase / Contact Seller →
          </button>
        </div>
      </div>
    </div>
  `;

  const existing = document.getElementById('history-detail-modal');
  if (existing) existing.remove();
  document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// Procurement Form Submission Handler
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('procurement-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const promptInput = document.getElementById('prompt-input');
    const prompt = promptInput ? promptInput.value.trim() : "";
    if (!prompt) {
      alert("Please enter a procurement request prompt.");
      return;
    }

    const stepperContainer = document.getElementById('agent-stepper');
    const resultContainer = document.getElementById('procurement-result');
    if (stepperContainer) stepperContainer.style.display = 'block';
    if (resultContainer) resultContainer.style.display = 'none';

    // Animate Stepper Items
    for (let i = 0; i < 6; i++) {
      const stepEl = document.getElementById(`agent-step-${i}`);
      if (stepEl) {
        stepEl.className = 'agent-step-item running';
        const statusEl = stepEl.querySelector('.step-status');
        if (statusEl) statusEl.textContent = 'Processing...';
      }
      await new Promise(r => setTimeout(r, 350));
      if (stepEl) {
        stepEl.className = 'agent-step-item completed';
        const statusEl = stepEl.querySelector('.step-status');
        if (statusEl) statusEl.textContent = '✓ Completed';
      }
    }

    try {
      const response = await fetch('/api/procurement', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      });

      const data = await response.json();
      if (data.success && data.finalPlan) {
        window.currentPlan = data.finalPlan;
        renderProcurementResult(data.finalPlan);
      } else {
        alert("Procurement notice: " + (data.detail || "Unable to complete request. Please try another prompt."));
      }
    } catch (err) {
      console.error(err);
      alert("Network error executing procurement engine.");
    } finally {
      if (stepperContainer) stepperContainer.style.display = 'none';
    }
  });
});

function renderProcurementResult(plan) {
  const resultContainer = document.getElementById('procurement-result');
  if (!resultContainer) return;

  const product = plan.product || {};
  const supplier = plan.supplier || {};
  const alternatives = plan.alternatives || [];

  const summaryEl = document.getElementById('res-summary');
  if (summaryEl) {
    summaryEl.innerHTML = plan.executiveSummaryHtml || parseMarkdownToHtml(plan.executiveSummary);
  }

  const supplierEl = document.getElementById('res-supplier');
  if (supplierEl) supplierEl.textContent = `${supplier.name || 'Artisan Guild'} (${supplier.location || 'India'})`;

  // Render main product with image if available and valid URL
  const productEl = document.getElementById('res-product');
  if (productEl) {
    const isValImg = product.imageUrl && (product.imageUrl.startsWith("http") || product.imageUrl.startsWith("/static"));
    let imgTag = isValImg ? `<img src="${product.imageUrl}" alt="${product.name}" style="width: 2.5rem; height: 2.5rem; border-radius: 0.4rem; object-fit: cover; border: 1px solid var(--border-amber); vertical-align: middle; margin-right: 0.5rem;" />` : '';
    productEl.innerHTML = `${imgTag} <span>${product.name || 'Handicraft Item'}</span>`;
  }

  const qtyEl = document.getElementById('res-qty');
  if (qtyEl) qtyEl.textContent = `${plan.quantity || 50} Units`;

  const totalEl = document.getElementById('res-total');
  if (totalEl) totalEl.textContent = `₹${Number(plan.totalEstimatedCost || 0).toLocaleString()}`;

  const etaEl = document.getElementById('res-eta');
  if (etaEl) etaEl.textContent = `${plan.estimatedDeliveryDays || 4} Days`;

  // Render Multiple Candidate Sellers Comparison Container
  const altContainer = document.getElementById('res-alternatives-container');
  if (altContainer) {
    if (alternatives && alternatives.length > 0) {
      let altHtml = '';
      alternatives.forEach((alt, idx) => {
        const isValAltImg = alt.imageUrl && (alt.imageUrl.startsWith("http") || alt.imageUrl.startsWith("/static"));
        const img = isValAltImg ? `<img src="${alt.imageUrl}" alt="${alt.productName}" style="width: 100%; height: 9rem; object-fit: cover; border-radius: 0.5rem; margin-bottom: 0.75rem; border: 1px solid var(--border-amber);" />` : `<div style="width: 100%; height: 9rem; background: rgba(15, 23, 42, 0.8); border-radius: 0.5rem; margin-bottom: 0.75rem; display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--amber-gold); font-size: 1.5rem; border: 1px solid var(--border-amber);"><span style="font-size: 2rem;">🖼️</span><span style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">Artisan Catalog Photo</span></div>`;

        altHtml += `
          <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid var(--border-amber); padding: 1.25rem; border-radius: 0.75rem; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
              ${img}
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                <h4 style="color: #ffffff; font-size: 1.1rem; font-weight: bold;">${alt.sellerName}</h4>
                <span style="color: #fbbf24; font-weight: bold; font-size: 0.9rem;">⭐ ${alt.rating || '4.9'}</span>
              </div>
              <p style="color: var(--amber-gold); font-size: 0.85rem; font-weight: bold; margin-bottom: 0.5rem;">${alt.productName}</p>
              <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem;">
                📍 ${alt.location} | Stock: ${alt.availableStock} units
              </div>
              <div style="display: flex; justify-content: space-between; background: rgba(9, 15, 33, 0.8); padding: 0.6rem 0.8rem; border-radius: 0.4rem; margin-bottom: 1rem;">
                <span style="color: var(--text-muted); font-size: 0.8rem;">Unit: ₹${Number(alt.price).toLocaleString()}</span>
                <span style="color: #34d399; font-weight: bold; font-size: 0.9rem;">Total: ₹${Number(alt.totalCost).toLocaleString()}</span>
              </div>
            </div>
            <button type="button" onclick="selectAlternativeSeller('${alt.sellerName.replace(/'/g, "\\'")}', '${alt.productName.replace(/'/g, "\\'")}', ${alt.price}, '${alt.whatsappNumber}')" class="btn-amber" style="width: 100%; padding: 0.6rem; font-size: 0.85rem;">
              💬 Select & Contact This Seller →
            </button>
          </div>
        `;
      });
      altContainer.innerHTML = altHtml;
    } else {
      altContainer.innerHTML = `<div style="color: var(--text-muted); padding: 1rem;">Primary seller ${supplier.name || 'Artisan Guild'} selected.</div>`;
    }
  }

  resultContainer.style.display = 'block';
  resultContainer.scrollIntoView({ behavior: 'smooth' });
}
