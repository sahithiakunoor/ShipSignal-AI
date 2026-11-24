import {test,expect} from '@playwright/test';
test('verified numerical answers and cited Portuguese customer evidence',async({page,request})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const actual=await (await request.get('/api/analytics')).json();
 await page.goto('/');await page.getByRole('button',{name:'Evidence assistant',exact:true}).click();
 await page.getByLabel('Your question',{exact:true}).fill('What is the late delivery rate?');
 await page.getByRole('button',{name:'Ask ShipSignal',exact:true}).click();
 await expect(page.getByTestId('assistant-answer')).toContainText(actual.kpis.orders.toLocaleString('en-US'),{timeout:60000});
 await expect(page.getByTestId('assistant-answer')).toContainText('sql:delivery_overview_v1');
 await page.getByLabel('Your question',{exact:true}).fill('A entrega está atrasada e sem previsão de quando vai chegar');
 await page.getByLabel('Evidence mode',{exact:true}).selectOption('reviews');
 await page.getByRole('button',{name:'Ask ShipSignal',exact:true}).click();
 await expect(page.getByTestId('assistant-answer')).toContainText('review:2232:0',{timeout:60000});
 await expect(page.getByText('ACTUAL CUSTOMER REVIEW',{exact:true}).first()).toBeVisible();
 await page.getByRole('button',{name:'Inspect original text'}).first().click();
 await page.evaluate(()=>window.scrollTo(0,0));
 await page.screenshot({path:'../docs/screenshots/assistant-desktop.png',fullPage:true});
 expect(errors).toEqual([]);
});
test('unsupported live shipment requests are explicitly declined',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Evidence assistant',exact:true}).click();
 await page.getByLabel('Your question',{exact:true}).fill('Where is my package right now?');
 await page.getByRole('button',{name:'Ask ShipSignal',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Insufficient evidence',exact:true})).toBeVisible();
 await expect(page.getByTestId('assistant-answer')).toContainText('outside the historical Olist dataset');
});
