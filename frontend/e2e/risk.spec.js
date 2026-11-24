import {test,expect} from '@playwright/test';
test('saved historical model metrics and risk explorer agree with API',async({page,request})=>{
 const response=await request.get('/api/risks?limit=25');expect(response.ok()).toBeTruthy();const actual=await response.json();
 await page.goto('/');await page.getByRole('button',{name:'Delivery risk',exact:true}).click();
 await expect(page.getByTestId('Test cohort')).toHaveText(actual.report.candidates[actual.report.selected_model].test.orders.toLocaleString('en-US'));
 await expect(page.getByRole('heading',{name:'Historical risk explorer'})).toBeVisible();
 await page.getByRole('button',{name:'Inspect order '+actual.items[0].order_id}).click();
 await expect(page.getByRole('heading',{name:'Selected historical prediction'})).toBeVisible();
 await expect(page.getByText(actual.items[0].order_id,{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Recompute from approval-time features',exact:true}).click();
 await expect(page.getByTestId('recomputed-risk')).toContainText('Matches saved prediction');
 await page.evaluate(()=>window.scrollTo(0,0));
 await page.screenshot({path:'../docs/screenshots/risk-desktop.png',fullPage:true});
});
