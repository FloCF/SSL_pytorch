from os import path
import time

import torch
from torch.optim import lr_scheduler

from utils import check_existing_model, Linear_Protocoler

class Trainer(object):
    def __init__(self, model, ssl_data, device='cuda'):
        # Define device
        self.device = torch.device(device)
        
        # Init
        self.loss_hist = []
        self.eval_acc = {'lin': [], 'knn': []}
        self._iter_scheduler = False
        
        # Model
        self.model = model
        
        # Define data
        self.data = ssl_data
    
    def train_epoch(self):
        for (x1,x2), _ in self.data.train_dl:
            x1,x2 = x1.to(self.device), x2.to(self.device)
        
            # Forward pass
            loss = self.model(x1,x2)
        
            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
        
            if self._iter_scheduler:
                # Scheduler every iteration for cosine deday
                self.scheduler.step()
        
            # Save loss
            self._epoch_loss += loss.item()
    
    def evaluate(self,):
        # Linear protocol
            evaluator = Linear_Protocoler(self.model.backbone_net, repre_dim=model.repre_dim, device=device)
            # knn accuracy
            eval_acc['knn'].append(evaluator.knn_accuracy(ssl_data.train_eval_dl, ssl_data.test_dl))
            # linear protocol
            evaluator.train(ssl_data.train_eval_dl, eval_params)
            eval_acc['lin'].append(evaluator.linear_accuracy(ssl_data.test_dl))
            # print
            print(f'Accuracy after epoch {epoch}: KNN:{eval_acc["knn"][-1]}, Linear: {eval_acc["lin"][-1]}')
    
    def train(self, save_root, train_params, optim_params, scheduler_params):
        # Check for trained model
        train_params['epoch_start'], saved_data = check_existing_model(save_root, self.device)
        
        # Define optimizer
        self.optimizer = train_params['optimizer'](self.model.parameters(), **optim_params)
        
        # Define scheduler
        train_len = len(self.data.train_dl)
        # If with warmup
        if 'warmup_epochs' in scheduler_params.keys() and train_params['epoch_start'] > train_params['warmup_epchs']:
            self.scheduler = lr_scheduler.LambdaLR(optimizer,
                                                   lambda it: (it+1)/(train_params['warmup_epchs']*train_len))
            self._iter_scheduler = True
        else:
            if train_params['scheduler']:
                self.scheduler = train_params['scheduler'](self.optimizer, **scheduler_params)
                self._iter_scheduler = train_params['iter_scheduler']
            else: # scheduler = None 
                self.scheduler = train_params['scheduler']
        
        # Extract saved data
        if saved_data:
            self.model.load_state_dict(saved_data['model'])
            self.optimizer.load_state_dict(saved_data['optim'])
            self.scheduler.load_state_dict(saved_data['sched'])
            self.loss_hist = saved_data['loss_hist']
            self.eval_acc = saved_data['eval_acc']
        
        # Run Training
        for epoch in range(train_params['epoch_start'], train_params['num_epochs']):
            self._epoch_loss = 0
            start_time = time.time()
            
            self.train_epoch()
    
        # Switch to new schedule after warmup period
        if 'warmup_epochs' in scheduler_params.keys() and epoch+1==train_params['warmup_epchs']:
            if train_params['scheduler']:
                self.scheduler = train_params['scheduler'](self.optimizer, **scheduler_params)
                iter_scheduler = train_params['iter_scheduler']
            else: # scheduler = None 
                self.scheduler = train_params['scheduler']
    
        # Log
        self.loss_hist.append(self._epoch_loss/train_len)
        if verbose:
            print(f'Epoch: {epoch}, Loss: {loss_hist[-1]}, Time epoch: {time.time() - start_time}')
    
        # Run evaluation
        if (epoch+1) in eval_params['evaluate_at']:
            # Linear protocol
            evaluator = Linear_Protocoler(model.backbone_net, repre_dim=model.repre_dim, device=device)
            # knn accuracy
            eval_acc['knn'].append(evaluator.knn_accuracy(ssl_data.train_eval_dl, ssl_data.test_dl))
            # linear protocol
            evaluator.train(ssl_data.train_eval_dl, eval_params)
            eval_acc['lin'].append(evaluator.linear_accuracy(ssl_data.test_dl))
            # print
            print(f'Accuracy after epoch {epoch}: KNN:{eval_acc["knn"][-1]}, Linear: {eval_acc["lin"][-1]}')
        
            torch.save({'model': model.state_dict(),
                        'optim': optimizer.state_dict(),
                        'sched': scheduler.state_dict(),
                        'loss_hist': loss_hist,
                        'eval_acc': eval_acc},
                       path.join(save_root, f'epoch_{epoch+1:03}.tar'))
            
def cifar10_trainer(save_root, model, ssl_data, optim_params, train_params,
                    eval_params, verbose = True):    
    
    # Extract device
    device = next(model.parameters()).device
    # Init
    loss_hist = []
    eval_acc = {'lin': [], 'knn': []}
    # Define optimizer
    optimizer = LARS(model.parameters(), **optim_params)
    # Define scheduler for warmup
    scheduler = lr_scheduler.LambdaLR(optimizer, lambda it : (it+1)/(train_params['warmup_epchs']*len(ssl_data.train_dl)))
    
    # Check for trained model
    train_params['epoch_start'], saved_data = check_existing_model(save_root, device)
    # Extract data
    if saved_data:
        model.load_state_dict(saved_data['model'])
        optimizer.load_state_dict(saved_data['optim'])
        if train_params['epoch_start'] >= train_params['warmup_epchs']:
            iters_left = (train_params['num_epochs']-train_params['warmup_epchs'])*len(ssl_data.train_dl)
            scheduler = lr_scheduler.CosineAnnealingLR(optimizer,
                                                       iters_left,
                                                       eta_min=train_params['eta_min'])
        scheduler.load_state_dict(saved_data['sched'])
        loss_hist = saved_data['loss_hist']
        eval_acc = saved_data['eval_acc']
        
    if scheduler is None:
        # Define scheduler for warmup
        scheduler = lr_scheduler.LambdaLR(optimizer, lambda it : (it+1)/(train_params['warmup_epchs']*len(ssl_data.train_dl)))
    
    # Run Training
    for epoch in range(train_params['epoch_start'], train_params['num_epochs']):
        epoch_loss = 0
        start_time = time.time()
        for (x1,x2), _ in ssl_data.train_dl:
            x1,x2 = x1.to(device), x2.to(device)
        
            # Forward pass
            loss = model(x1,x2)
        
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        
            # Scheduler every iteration for cosine deday
            scheduler.step()
        
            # Save loss
            epoch_loss += loss.item()
    
        # Switch to Cosine Decay after warmup period
        if epoch+1==train_params['warmup_epchs']:
            iters_left = (train_params['num_epochs']-train_params['warmup_epchs'])*len(ssl_data.train_dl)
            scheduler = lr_scheduler.CosineAnnealingLR(optimizer,
                                                       iters_left,
                                                       eta_min=train_params['eta_min'])
    
        # Log
        loss_hist.append(epoch_loss/len(ssl_data.train_dl))
        if verbose:
            print(f'Epoch: {epoch}, Loss: {loss_hist[-1]}, Time epoch: {time.time() - start_time}')
    
        # Run evaluation
        if (epoch+1) in eval_params['evaluate_at']:
            # Linear protocol
            evaluator = Linear_Protocoler(model.backbone_net, repre_dim=model.repre_dim, device=device)
            # knn accuracy
            eval_acc['knn'].append(evaluator.knn_accuracy(ssl_data.train_eval_dl, ssl_data.test_dl))
            # linear protocol
            evaluator.train(ssl_data.train_eval_dl, eval_params)
            eval_acc['lin'].append(evaluator.linear_accuracy(ssl_data.test_dl))
            # print
            print(f'Accuracy after epoch {epoch}: KNN:{eval_acc["knn"][-1]}, Linear: {eval_acc["lin"][-1]}')
        
            torch.save({'model': model.state_dict(),
                        'optim': optimizer.state_dict(),
                        'sched': scheduler.state_dict(),
                        'loss_hist': loss_hist,
                        'eval_acc': eval_acc},
                       path.join(save_root, f'epoch_{epoch+1:03}.tar'))